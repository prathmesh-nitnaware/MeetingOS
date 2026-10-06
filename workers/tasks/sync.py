import asyncio
import logging
from typing import Any
from uuid import uuid4

from packages.common.enums import ProcessingStatus
from packages.common.models import Meeting
from packages.connectors import ConnectorNotImplementedError, connector_registry
from packages.memory.database import dispose_engine, get_db_session
from packages.memory.models import JobModel, MeetingModel
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from sqlalchemy import select

from workers.celery_app import celery_app
from workers.tasks.ingestion import get_embedder_provider, normalize_segment_ids

logger = logging.getLogger(__name__)


async def run_connector_ingestion(
    meeting: Meeting,
    job_id: str,
    database_url: str,
    org_id: str = "org_dev",
) -> dict[str, Any]:
    """Run NLP extraction and embeddings directly on a connector meeting (no speech step)."""
    embedder = get_embedder_provider()
    nlp_pipe = NLPExtractionPipeline()
    segments = normalize_segment_ids(meeting.meeting_id, meeting.segments)
    meeting = meeting.model_copy(update={"segments": segments})

    async with get_db_session(database_url) as session:
        repo = MeetingRepository(session)

        # Idempotency: the same external meeting is only ingested once per organisation
        existing = (
            await session.execute(
                select(MeetingModel.id).where(
                    MeetingModel.org_id == org_id,
                    MeetingModel.source_provider == meeting.source_provider,
                    MeetingModel.external_meeting_id == meeting.external_meeting_id,
                )
            )
        ).first()
        if existing:
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.SUCCEEDED,
                stage="skipped",
                progress=1.0,
                error_message="Skipped: Duplicate external meeting.",
            )
            return {"status": "skipped", "reason": "duplicate"}

        await repo.update_job(
            job_id=job_id, status=ProcessingStatus.RUNNING, stage="saving_meeting", progress=0.1
        )
        meeting_row = await repo.create_meeting(meeting, org_id=org_id)
        meeting_id = meeting_row.id
        await repo.update_meeting_status(meeting_id, status=ProcessingStatus.RUNNING)

    try:
        nlp_results = await nlp_pipe.process_transcript(
            meeting_id=meeting_id,
            segments=segments,
            meeting_date=meeting.meeting_date,
        )

        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="generating_embeddings",
                progress=0.4,
            )

        segment_texts = [s.text for s in segments]
        vectors = await embedder.embed(segment_texts) if segment_texts else []
        embedding_records = [
            ("segment", seg.segment_id, seg.text, vec)
            for seg, vec in zip(segments, vectors, strict=False)
        ]

        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="persisting_knowledge",
                progress=0.7,
            )
            await repo.save_nlp_extraction_results(meeting_id, nlp_results)
            await repo.save_embeddings(meeting_id, embedding_records)
            await repo.save_evidence_records(meeting_id, nlp_results.evidence)

            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="temporal_reconciliation",
                progress=0.9,
            )
            temporal_engine = TemporalIntelligenceEngine(session, org_id=org_id)
            reconcile_res = await temporal_engine.reconcile_meeting_lifecycle(meeting_id)

            await repo.update_meeting_status(meeting_id, status=ProcessingStatus.SUCCEEDED)
            await repo.update_job(
                job_id=job_id, status=ProcessingStatus.SUCCEEDED, stage="completed", progress=1.0
            )

        return {
            "status": "succeeded",
            "meeting_id": meeting_id,
            "segments_count": len(segments),
            "entities_count": len(nlp_results.entities),
            "decisions_count": len(nlp_results.decisions),
            "commitments_count": len(nlp_results.commitments),
            "issues_count": len(nlp_results.issues),
            "temporal_events_created": reconcile_res.events_created,
        }
    except Exception as exc:
        logger.exception("Connector Ingestion failed: %s", exc)
        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.FAILED,
                stage="failed",
                progress=1.0,
                error_message=str(exc),
            )
            await repo.update_meeting_status(meeting_id, status=ProcessingStatus.FAILED)
        raise


async def run_sync_pipeline(provider: str, org_id: str, database_url: str) -> dict[str, Any]:
    """Fetch the provider's meetings and ingest new ones into ``org_id``."""
    from apps.api.providers import build_connector_config

    connector = connector_registry.get(provider)
    config = build_connector_config(provider)

    if not config.enabled:
        raise ValueError(f"Sync failed: the '{provider}' connector is disabled.")
    if not connector.validate_config(config):
        raise ValueError(f"Sync failed: Configuration is invalid for provider '{provider}'.")

    ext_meetings = await connector.list_meetings(config)
    ingested = 0
    skipped = 0
    errors: list[str] = []

    for ext_m in ext_meetings:
        cmf_meeting = connector.normalize_to_cmf(ext_m)
        # Meeting IDs are global primary keys: qualify them per organisation
        cmf_meeting = cmf_meeting.model_copy(
            update={"meeting_id": f"{cmf_meeting.meeting_id}-{org_id}"}
        )

        job_id = str(uuid4())
        async with get_db_session(database_url) as session:
            session.add(
                JobModel(
                    id=job_id,
                    org_id=org_id,
                    status=ProcessingStatus.QUEUED.value,
                    stage="sync_initialized",
                    progress=0.0,
                )
            )

        try:
            ingest_res = await run_connector_ingestion(cmf_meeting, job_id, database_url, org_id)
            if ingest_res.get("status") == "skipped":
                skipped += 1
            else:
                ingested += 1
        except Exception as e:
            errors.append(f"Failed to ingest meeting {ext_m.external_id}: {e}")

    return {
        "provider": provider,
        "org_id": org_id,
        "discovered": len(ext_meetings),
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(name="tasks.sync_connector", bind=True, max_retries=3)
def sync_connector_task(self: Any, provider: str, org_id: str) -> dict[str, Any]:
    """Celery task running a connector sync for one organisation. Credentials and the database
    URL come from the worker's own settings, never from (plain-text) task arguments."""
    from apps.api.config import settings

    async def run() -> dict[str, Any]:
        try:
            return await run_sync_pipeline(provider, org_id, settings.database_url)
        finally:
            await dispose_engine()

    try:
        return asyncio.run(run())
    except (ValueError, ConnectorNotImplementedError):
        # Configuration / authentication problems are not transient: do not retry
        raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries * 5)

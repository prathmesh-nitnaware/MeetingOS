import asyncio
import logging
from typing import Any
from uuid import uuid4

from packages.common.enums import ProcessingStatus
from packages.common.models import Meeting
from packages.connectors import ConnectorConfig, connector_registry
from packages.memory.database import get_db_session
from packages.memory.models import JobModel, MeetingModel
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from sqlalchemy import select

from workers.celery_app import celery_app
from workers.tasks.ingestion import get_embedder_provider

logger = logging.getLogger(__name__)


async def run_connector_ingestion(
    meeting: Meeting,
    job_id: str,
    database_url: str,
) -> dict[str, Any]:
    """Directly run NLP extraction and embedding generation on CMF objects, avoiding speech transcription."""
    embedder = get_embedder_provider("mock")
    nlp_pipe = NLPExtractionPipeline()

    async with get_db_session(database_url) as session:
        repo = MeetingRepository(session)

        # Idempotency check: verify meeting was not ingested concurrently
        stmt = select(MeetingModel).where(
            MeetingModel.source_provider == meeting.source_provider,
            MeetingModel.external_meeting_id == meeting.external_meeting_id,
        )
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
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
        meeting_row = await repo.create_meeting(meeting)
        meeting_id = meeting_row.id
        await repo.update_meeting_status(meeting_id, status=ProcessingStatus.RUNNING)

    try:
        # NLP Extraction
        nlp_results = await nlp_pipe.process_transcript(
            meeting_id=meeting_id,
            segments=meeting.segments,
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

        # Generate vectors
        segment_texts = [s.text for s in meeting.segments]
        vectors = await embedder.embed(segment_texts) if segment_texts else []
        embedding_records = []
        for seg, vec in zip(meeting.segments, vectors, strict=False):
            embedding_records.append(("segment", seg.segment_id, seg.text, vec))

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

            # Temporal Intelligence Reconciliation
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="temporal_reconciliation",
                progress=0.9,
            )
            temporal_engine = TemporalIntelligenceEngine(session)
            reconcile_res = await temporal_engine.reconcile_meeting_lifecycle(meeting_id)

            await repo.update_meeting_status(meeting_id, status=ProcessingStatus.SUCCEEDED)
            await repo.update_job(
                job_id=job_id, status=ProcessingStatus.SUCCEEDED, stage="completed", progress=1.0
            )

        return {
            "status": "succeeded",
            "meeting_id": meeting_id,
            "segments_count": len(meeting.segments),
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


async def run_sync_pipeline(
    provider: str,
    config_dict: dict[str, Any],
    database_url: str,
) -> dict[str, Any]:
    """Retrieve external meetings, filter duplicates, and run parallel direct ingestions."""
    connector = connector_registry.get(provider)
    config = ConnectorConfig(provider=provider, **config_dict)

    if not connector.validate_config(config):
        raise ValueError(f"Sync failed: Configuration is invalid for provider '{provider}'.")

    # Retrieve external meetings list
    ext_meetings = await connector.list_meetings(config)
    discovered = len(ext_meetings)
    ingested = 0
    skipped = 0
    errors = []

    for ext_m in ext_meetings:
        async with get_db_session(database_url) as session:
            # Deduplication
            stmt = select(MeetingModel).where(
                MeetingModel.source_provider == provider,
                MeetingModel.external_meeting_id == ext_m.external_id,
            )
            res = await session.execute(stmt)
            if res.scalar_one_or_none():
                skipped += 1
                continue

            # Create Job entry
            job_id = str(uuid4())
            job_row = JobModel(
                id=job_id,
                status=ProcessingStatus.QUEUED.value,
                stage="sync_initialized",
                progress=0.0,
            )
            session.add(job_row)
            await session.commit()

        try:
            # Normalize to CMF and Ingest
            cmf_meeting = connector.normalize_to_cmf(ext_m)
            ingest_res = await run_connector_ingestion(cmf_meeting, job_id, database_url)
            if ingest_res.get("status") == "skipped":
                skipped += 1
            else:
                ingested += 1
        except Exception as e:
            errors.append(f"Failed to ingest meeting {ext_m.external_id}: {str(e)}")

    return {
        "provider": provider,
        "discovered": discovered,
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(name="tasks.sync_connector", bind=True, max_retries=3)
def sync_connector_task(
    self: Any, provider: str, config_dict: dict[str, Any], database_url: str
) -> dict[str, Any]:
    """Celery background task orchestrating the connector sync loop."""
    try:
        return asyncio.run(run_sync_pipeline(provider, config_dict, database_url))
    except Exception as exc:
        # Non-retryable errors
        err_msg = str(exc)
        if "Authentication failed" in err_msg or "Configuration is invalid" in err_msg:
            raise

        # Retry other transient errors (e.g. db connection drop) with bounded exponential backoff
        countdown = 2**self.request.retries * 5
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except Exception:
            raise

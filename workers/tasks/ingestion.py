import asyncio
import logging
from pathlib import Path
from typing import Any

from packages.common.enums import ProcessingStatus, SourceType
from packages.ingestion.pipeline import IngestionPipeline
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.mock import MockEmbedder
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.speech.interfaces import BaseASR, BaseDiarizer
from packages.speech.mock import MockASR, MockDiarizer

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_speech_providers(
    asr_name: str = "mock", diarizer_name: str = "mock"
) -> tuple[BaseASR, BaseDiarizer]:
    """Factory to instantiate ASR and Diarizer providers by name."""
    _ = (asr_name, diarizer_name)
    asr = MockASR()
    diarizer = MockDiarizer()
    return asr, diarizer


def get_embedder_provider(embedder_name: str = "mock") -> BaseEmbedder:
    """Factory to instantiate Embedder provider by name."""
    _ = embedder_name
    return MockEmbedder()


async def run_ingestion_pipeline(
    meeting_id: str,
    job_id: str,
    file_path_str: str,
    source_type_str: str,
    database_url: str,
    asr_provider_name: str = "mock",
    diarizer_provider_name: str = "mock",
    embedder_provider_name: str = "mock",
) -> dict[str, Any]:
    """Execute end-to-end speech ingestion, NLP fact extraction, and vector embedding pipeline."""
    file_path = Path(file_path_str)
    source_type = SourceType(source_type_str)
    asr, diarizer = get_speech_providers(asr_provider_name, diarizer_provider_name)
    embedder = get_embedder_provider(embedder_provider_name)
    ingestion_pipe = IngestionPipeline(asr_provider=asr, diarizer_provider=diarizer)
    nlp_pipe = NLPExtractionPipeline()

    async with get_db_session(database_url) as session:
        repo = MeetingRepository(session)
        await repo.update_job(
            job_id=job_id, status=ProcessingStatus.RUNNING, stage="speech_processing", progress=0.2
        )
        await repo.update_meeting_status(meeting_id=meeting_id, status=ProcessingStatus.RUNNING)

    try:
        # 1. Speech Transcription & Diarization
        segments, speakers, duration = await ingestion_pipe.process_file(
            file_path, source_type=source_type
        )

        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="nlp_fact_extraction",
                progress=0.5,
            )
            await repo.save_transcript_segments(meeting_id, segments, speakers)
            await repo.update_meeting_status(
                meeting_id, status=ProcessingStatus.RUNNING, duration_seconds=duration
            )

        # 2. NLP Extraction Pipeline
        meeting_obj = None
        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            meeting_obj = await repo.get_meeting(meeting_id)

        ref_date = meeting_obj.meeting_date if meeting_obj else None
        nlp_results = await nlp_pipe.process_transcript(
            meeting_id=meeting_id,
            segments=segments,
            meeting_date=ref_date,
        )

        # 3. Dense Vector Embeddings Generation
        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="generating_embeddings",
                progress=0.75,
            )

        segment_texts = [s.text for s in segments]
        vectors = await embedder.embed(segment_texts) if segment_texts else []
        embedding_records: list[tuple[str, str, str, list[float]]] = []
        for seg, vec in zip(segments, vectors, strict=False):
            embedding_records.append(("segment", seg.segment_id, seg.text, vec))

        # 4. Persist NLP Facts, Embeddings, and Evidence Records
        async with get_db_session(database_url) as session:
            repo = MeetingRepository(session)
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="persisting_knowledge",
                progress=0.85,
            )
            await repo.save_nlp_extraction_results(meeting_id, nlp_results)
            await repo.save_embeddings(meeting_id, embedding_records)
            await repo.save_evidence_records(meeting_id, nlp_results.evidence)

            # 5. Temporal Intelligence Reconciliation across meetings
            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="temporal_reconciliation",
                progress=0.95,
            )
            temporal_engine = TemporalIntelligenceEngine(session)
            reconcile_res = await temporal_engine.reconcile_meeting_lifecycle(meeting_id)

            await repo.update_meeting_status(
                meeting_id, status=ProcessingStatus.SUCCEEDED, duration_seconds=duration
            )
            await repo.update_job(
                job_id=job_id, status=ProcessingStatus.SUCCEEDED, stage="completed", progress=1.0
            )

        return {
            "status": "succeeded",
            "meeting_id": meeting_id,
            "job_id": job_id,
            "segments_count": len(segments),
            "speakers_count": len(speakers),
            "entities_count": len(nlp_results.entities),
            "decisions_count": len(nlp_results.decisions),
            "commitments_count": len(nlp_results.commitments),
            "issues_count": len(nlp_results.issues),
            "embeddings_count": len(embedding_records),
            "evidence_count": len(nlp_results.evidence),
            "temporal_events_created": reconcile_res.events_created,
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.exception("Ingestion failed for meeting %s: %s", meeting_id, exc)
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


@celery_app.task(name="tasks.process_meeting_ingestion", bind=True)
def process_meeting_task(
    self: Any,
    meeting_id: str,
    job_id: str,
    file_path_str: str,
    source_type_str: str,
    database_url: str,
    asr_provider_name: str = "mock",
    diarizer_provider_name: str = "mock",
    embedder_provider_name: str = "mock",
) -> dict[str, Any]:
    """Celery task entry point running the async ingestion pipeline in an event loop."""
    _ = self
    return asyncio.run(
        run_ingestion_pipeline(
            meeting_id=meeting_id,
            job_id=job_id,
            file_path_str=file_path_str,
            source_type_str=source_type_str,
            database_url=database_url,
            asr_provider_name=asr_provider_name,
            diarizer_provider_name=diarizer_provider_name,
            embedder_provider_name=embedder_provider_name,
        )
    )

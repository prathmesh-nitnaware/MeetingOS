import asyncio
import logging
from pathlib import Path
from typing import Any

from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import TranscriptSegment
from packages.ingestion.pipeline import IngestionPipeline
from packages.memory.database import dispose_engine, get_db_session
from packages.memory.repository import MeetingRepository
from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.speech.interfaces import BaseASR, BaseDiarizer
from packages.speech.whisper import SpeechProviderUnavailableError

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_speech_providers(
    asr_name: str | None = None, diarizer_name: str | None = None
) -> tuple[BaseASR, BaseDiarizer]:
    """ASR and diarizer for the given names, defaulting to ASR_PROVIDER / DIARIZER_PROVIDER."""
    from apps.api.providers import build_speech_providers

    return build_speech_providers(asr_name, diarizer_name)


def get_embedder_provider(embedder_name: str | None = None) -> BaseEmbedder:
    """Embedder for the given name, defaulting to MEETINGOS_EMBEDDING_PROVIDER."""
    from apps.api.providers import build_embedder

    if embedder_name:
        from packages.providers.embeddings import get_embedder

        return get_embedder(embedder_name)
    return build_embedder()


def normalize_segment_ids(
    meeting_id: str, segments: list[TranscriptSegment]
) -> list[TranscriptSegment]:
    """Give every segment the meeting-prefixed ID it is stored under.

    Facts, events and evidence reference segments by ID; extracting them from un-prefixed IDs
    (``seg-003``) while the transcript is stored as ``<meeting>-seg-003`` left every "jump to
    evidence" link and decision timestamp dangling.
    """
    normalized: list[TranscriptSegment] = []
    for seg in segments:
        seg_id = seg.segment_id
        if not seg_id.startswith(f"{meeting_id}-"):
            seg_id = f"{meeting_id}-{seg_id}"
        normalized.append(seg.model_copy(update={"segment_id": seg_id}))
    return normalized


def _friendly_error(exc: Exception) -> str:
    """Message stored on the job and shown to users. Only validation and speech-setup errors
    are written for users; anything else (database, network, bugs) may contain internal
    details, which stay in the server log."""
    if not isinstance(exc, ValueError | SpeechProviderUnavailableError):
        return "Processing failed because of an internal error. Details are in the server log."
    message = str(exc) or type(exc).__name__
    return message if len(message) <= 500 else message[:497] + "..."


async def run_ingestion_pipeline(
    meeting_id: str,
    job_id: str,
    file_path_str: str,
    source_type_str: str,
    database_url: str,
    org_id: str = "org_dev",
    asr_provider_name: str | None = None,
    diarizer_provider_name: str | None = None,
    embedder_provider_name: str | None = None,
) -> dict[str, Any]:
    """Speech transcription, NLP fact extraction, embeddings and temporal reconciliation."""
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
        # 1. Speech Transcription & Diarization (or text/subtitle parsing)
        raw_segments, speakers, duration = await ingestion_pipe.process_file(
            file_path, source_type=source_type
        )
        segments = normalize_segment_ids(meeting_id, raw_segments)

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
            meeting_obj = await repo.get_meeting(meeting_id, org_id=org_id)

        # 2. NLP Extraction Pipeline
        nlp_results = await nlp_pipe.process_transcript(
            meeting_id=meeting_id,
            segments=segments,
            meeting_date=meeting_obj.meeting_date if meeting_obj else None,
        )

        # 3. Dense Vector Embeddings
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
        embedding_records: list[tuple[str, str, str, list[float]]] = [
            ("segment", seg.segment_id, seg.text, vec)
            for seg, vec in zip(segments, vectors, strict=False)
        ]

        # 4. Persist NLP facts, embeddings and evidence; 5. reconcile with earlier meetings
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

            await repo.update_job(
                job_id=job_id,
                status=ProcessingStatus.RUNNING,
                stage="temporal_reconciliation",
                progress=0.95,
            )
            temporal_engine = TemporalIntelligenceEngine(session, org_id=org_id)
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
                error_message=_friendly_error(exc),
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
    org_id: str,
    asr_provider_name: str | None = None,
    diarizer_provider_name: str | None = None,
    embedder_provider_name: str | None = None,
) -> dict[str, Any]:
    """Celery entry point. The worker uses its own DATABASE_URL setting; credentials are never
    put into task arguments (they would sit in plain text in the Redis broker)."""
    from apps.api.config import settings

    _ = self

    async def run() -> dict[str, Any]:
        try:
            return await run_ingestion_pipeline(
                meeting_id=meeting_id,
                job_id=job_id,
                file_path_str=file_path_str,
                source_type_str=source_type_str,
                database_url=settings.database_url,
                org_id=org_id,
                asr_provider_name=asr_provider_name,
                diarizer_provider_name=diarizer_provider_name,
                embedder_provider_name=embedder_provider_name,
            )
        finally:
            await dispose_engine()

    return asyncio.run(run())

import asyncio
import json
import logging
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member, require_permission, require_viewer
from apps.api.config import settings
from apps.api.rate_limiter import rate_limit
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIssue,
    ExtractedRelation,
    Meeting,
    MeetingMetadata,
    Participant,
    SpeakerInfo,
    TranscriptSegment,
)
from packages.ingestion.validator import (
    FileValidationError,
    save_upload_file,
    validate_file_extension,
)
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.speech.whisper import AudioDecodeError, SpeechProviderUnavailableError
from pydantic import BaseModel, Field
from workers.tasks.ingestion import run_ingestion_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["Meetings"])

upload_rate_limit = rate_limit("upload", lambda: settings.rate_limit_upload_per_min)
extract_rate_limit = rate_limit("extract", lambda: settings.rate_limit_admin_per_min)

# Strong references to in-process background ingestions (fallback when no Celery broker).
# asyncio only keeps weak references to tasks, so an unreferenced task can be garbage
# collected before it finishes.
_background_ingestions: set[asyncio.Task[Any]] = set()

AUDIO_VIDEO_TYPES = {
    SourceType.AUDIO_WAV,
    SourceType.AUDIO_MP3,
    SourceType.AUDIO_M4A,
    SourceType.VIDEO_MP4,
}


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    job_id: str
    processing_status: ProcessingStatus
    title: str
    message: str = "Meeting ingestion job created successfully."


class MeetingSummaryResponse(BaseModel):
    meeting_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None = None
    source_type: SourceType
    processing_status: ProcessingStatus
    participant_count: int
    speaker_count: int = 0
    segment_count: int
    created_at: datetime


class MeetingDetailResponse(BaseModel):
    meeting_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None = None
    source_type: SourceType
    processing_status: ProcessingStatus
    participants: list[Participant] = Field(default_factory=list)
    speakers: list[SpeakerInfo] = Field(default_factory=list)
    speakers_count: int
    segments_count: int
    metadata: MeetingMetadata
    created_at: datetime
    updated_at: datetime
    latest_job_id: str | None = None
    latest_job_error: str | None = None


class TranscriptResponse(BaseModel):
    meeting_id: str
    segments_count: int
    segments: list[TranscriptSegment]


class ExtractionResponse(BaseModel):
    meeting_id: str
    entities_count: int
    topics_count: int
    decisions_count: int
    commitments_count: int
    issues_count: int
    events_count: int
    relations_count: int
    message: str = "NLP facts extracted and persisted successfully."


def _parse_meeting_date(meeting_date: str | None) -> datetime:
    if not meeting_date:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(meeting_date, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid meeting_date format '{meeting_date}'. Expected YYYY-MM-DD or an ISO date-time.",
            ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _dispatch_background_ingestion(kwargs: dict[str, Any]) -> str:
    """Queue ingestion on a Celery worker; fall back to an in-process task if no broker."""
    if settings.use_celery:
        try:
            from workers.tasks.ingestion import process_meeting_task

            process_meeting_task.delay(  # type: ignore[attr-defined]
                kwargs["meeting_id"],
                kwargs["job_id"],
                kwargs["file_path_str"],
                kwargs["source_type_str"],
                kwargs["org_id"],
            )
            return "celery"
        except Exception as exc:
            logger.warning(
                "Celery broker unavailable (%s); processing upload in the API process.", exc
            )

    async def run() -> None:
        try:
            await run_ingestion_pipeline(database_url=settings.database_url, **kwargs)
        except Exception:
            logger.exception("Background ingestion failed for %s", kwargs["meeting_id"])

    task = asyncio.create_task(run())
    _background_ingestions.add(task)
    task.add_done_callback(_background_ingestions.discard)
    return "in-process"


@router.post(
    "",
    response_model=MeetingCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(upload_rate_limit)],
)
async def create_and_upload_meeting(
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(min_length=1, max_length=500)],
    meeting_date: Annotated[str | None, Form()] = None,
    participants: Annotated[str | None, Form()] = None,
    async_processing: Annotated[bool, Form()] = False,
    user: UserIdentity = Depends(require_member),
) -> MeetingCreateResponse:
    """Upload a meeting audio/video/text file, create a meeting record, and trigger ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")
    if not title.strip():
        raise HTTPException(status_code=400, detail="Meeting title cannot be blank.")

    try:
        source_type = validate_file_extension(file.filename)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meeting_id = f"meet-{uuid4()}"
    job_id = f"job-{uuid4()}"
    parsed_date = _parse_meeting_date(meeting_date)

    parsed_participants: list[Participant] = []
    if participants:
        try:
            raw_parts = json.loads(participants)
            if isinstance(raw_parts, list):
                for p in raw_parts:
                    if isinstance(p, str) and p.strip():
                        parsed_participants.append(Participant(canonical_name=p))
                    elif isinstance(p, dict) and "canonical_name" in p:
                        parsed_participants.append(Participant(**p))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid participants JSON format: {exc}"
            ) from exc

    # Save uploaded file in tenant-scoped directory
    storage_dir = Path(settings.upload_storage_dir)
    file_ext = Path(file.filename).suffix.lower()
    tenant_meeting_dir = storage_dir / "orgs" / user.org_id / "meetings" / meeting_id
    tenant_meeting_dir.mkdir(parents=True, exist_ok=True)
    dest_path = tenant_meeting_dir / f"audio{file_ext}"

    try:
        file_size = save_upload_file(file.file, dest_path, max_size_mb=settings.max_upload_size_mb)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meeting = Meeting(
        meeting_id=meeting_id,
        title=title.strip(),
        meeting_date=parsed_date,
        source_type=source_type,
        processing_status=ProcessingStatus.QUEUED,
        participants=parsed_participants,
        metadata=MeetingMetadata(source_filename=file.filename, file_size_bytes=file_size),
    )

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await repo.create_meeting(meeting, org_id=user.org_id)
        await repo.create_job(
            job_id=job_id, meeting_id=meeting_id, stage="queued", org_id=user.org_id
        )

    ingestion_kwargs: dict[str, Any] = {
        "meeting_id": meeting_id,
        "job_id": job_id,
        "file_path_str": str(dest_path),
        "source_type_str": str(source_type),
        "org_id": user.org_id,
    }

    if async_processing:
        where = _dispatch_background_ingestion(ingestion_kwargs)
        return MeetingCreateResponse(
            meeting_id=meeting_id,
            job_id=job_id,
            processing_status=ProcessingStatus.QUEUED,
            title=meeting.title,
            message=f"Meeting queued for background processing ({where}).",
        )

    try:
        await run_ingestion_pipeline(database_url=settings.database_url, **ingestion_kwargs)
    except SpeechProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (AudioDecodeError, FileValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return MeetingCreateResponse(
        meeting_id=meeting_id,
        job_id=job_id,
        processing_status=ProcessingStatus.SUCCEEDED,
        title=meeting.title,
    )


@router.get("", response_model=list[MeetingSummaryResponse])
async def list_meetings(
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: UserIdentity = Depends(require_viewer),
) -> list[MeetingSummaryResponse]:
    """List the organisation's meetings (newest first). Total count is in X-Total-Count."""
    async with get_db_session(settings.database_url) as session:
        rows, total = await MeetingRepository(session).list_meeting_summaries(
            org_id=user.org_id, limit=limit, offset=offset
        )
    response.headers["X-Total-Count"] = str(total)
    return [MeetingSummaryResponse(**row) for row in rows]


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> MeetingDetailResponse:
    """Get full metadata, processing status, participants and speakers for a meeting."""
    from packages.memory.models import JobModel
    from sqlalchemy import select

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        latest_job = None
        if meeting:
            latest_job = (
                await session.execute(
                    select(JobModel)
                    .where(JobModel.meeting_id == meeting_id)
                    .order_by(JobModel.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting with ID '{meeting_id}' not found.")

    return MeetingDetailResponse(
        meeting_id=meeting.meeting_id,
        title=meeting.title,
        meeting_date=meeting.meeting_date,
        duration_seconds=meeting.duration_seconds,
        source_type=meeting.source_type,
        processing_status=meeting.processing_status,
        participants=meeting.participants,
        speakers=meeting.speakers,
        speakers_count=len(meeting.speakers),
        segments_count=len(meeting.segments),
        metadata=meeting.metadata,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        latest_job_id=latest_job.id if latest_job else None,
        latest_job_error=latest_job.error_message if latest_job else None,
    )


@router.delete("/{meeting_id}", response_model=dict[str, Any])
async def delete_meeting(
    meeting_id: str,
    hard_delete: bool = Query(
        default=False, description="Permanently delete rather than soft-deleting"
    ),
    user: UserIdentity = Depends(require_permission("meetings.delete")),
) -> dict[str, Any]:
    """Delete a meeting (admins/owners). Defaults to soft deletion for safety and recovery."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        if hard_delete:
            success = await repo.hard_delete_meeting(
                meeting_id=meeting_id,
                org_id=user.org_id,
                actor_id=user.user_id,
                upload_storage_dir=settings.upload_storage_dir,
            )
        else:
            success = await repo.soft_delete_meeting(
                meeting_id=meeting_id, actor_id=user.user_id, org_id=user.org_id
            )

        if not success:
            raise HTTPException(
                status_code=404, detail=f"Meeting with ID '{meeting_id}' not found."
            )
        await session.commit()
        return {
            "status": "succeeded",
            "meeting_id": meeting_id,
            "deletion_type": "hard_delete" if hard_delete else "soft_delete",
        }


@router.get("/{meeting_id}/audio")
async def get_meeting_audio(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> FileResponse:
    """Download the uploaded source file of a meeting (tenant-scoped), with its real media type."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id=meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

    storage_base = Path(settings.upload_storage_dir).resolve()
    tenant_dir = (storage_base / "orgs" / user.org_id / "meetings" / meeting_id).resolve()

    # Path traversal defense: ensure resolved path is strictly within storage_base
    try:
        tenant_dir.relative_to(storage_base)
    except ValueError:
        raise HTTPException(
            status_code=403, detail="Access denied: invalid storage path traversal."
        )

    if not tenant_dir.is_dir():
        raise HTTPException(status_code=404, detail="Source file not found on storage.")

    stored = sorted(tenant_dir.glob("audio.*"))
    if not stored:
        raise HTTPException(status_code=404, detail="Source file not found.")

    target_file = stored[0].resolve()
    try:
        target_file.relative_to(tenant_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal attempt detected.")

    suffix = target_file.suffix.lower()
    media_type = (
        {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".mp4": "video/mp4",
            ".txt": "text/plain",
            ".srt": "application/x-subrip",
        }.get(suffix)
        or mimetypes.guess_type(target_file.name)[0]
        or "application/octet-stream"
    )
    original = meeting.metadata.source_filename or f"{meeting.title or meeting_id}{suffix}"
    download_name = original if Path(original).suffix.lower() == suffix else f"{original}{suffix}"

    return FileResponse(path=target_file, media_type=media_type, filename=download_name)


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_meeting_transcript(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> TranscriptResponse:
    """Get all timestamped transcript segments for a meeting ordered by sequence."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(
                status_code=404, detail=f"Meeting with ID '{meeting_id}' not found."
            )
        segments = await repo.get_transcript_segments(meeting_id)

    return TranscriptResponse(
        meeting_id=meeting_id, segments_count=len(segments), segments=segments
    )


# --------------------------------------------------------------------------
# NLP Facts Sub-resource Endpoints
# --------------------------------------------------------------------------


async def _require_meeting(repo: MeetingRepository, meeting_id: str, org_id: str) -> Meeting:
    meeting = await repo.get_meeting(meeting_id, org_id=org_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
    return meeting


@router.get("/{meeting_id}/entities", response_model=list[ExtractedEntity])
async def get_meeting_entities(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedEntity]:
    """Retrieve all named and domain entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_entities(meeting_id)


@router.get("/{meeting_id}/topics", response_model=list[str])
async def get_meeting_topics(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[str]:
    """Retrieve discussion topics extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_topics(meeting_id)


@router.get("/{meeting_id}/decisions", response_model=list[ExtractedDecision])
async def get_meeting_decisions(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedDecision]:
    """Retrieve decisions extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_decisions(meeting_id)


@router.get("/{meeting_id}/actions", response_model=list[ExtractedCommitment])
async def get_meeting_actions(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedCommitment]:
    """Retrieve action items and commitments extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_actions(meeting_id)


@router.get("/{meeting_id}/issues", response_model=list[ExtractedIssue])
async def get_meeting_issues(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedIssue]:
    """Retrieve issues and problems extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_issues(meeting_id)


@router.get("/{meeting_id}/timeline", response_model=list[ExtractedEvent])
async def get_meeting_timeline(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedEvent]:
    """Retrieve chronological lifecycle events of the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_timeline(meeting_id)


@router.get("/{meeting_id}/relations", response_model=list[ExtractedRelation])
async def get_meeting_relations(
    meeting_id: str, user: UserIdentity = Depends(require_viewer)
) -> list[ExtractedRelation]:
    """Retrieve typed relations between entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await _require_meeting(repo, meeting_id, user.org_id)
        return await repo.get_meeting_relations(meeting_id)


@router.post(
    "/{meeting_id}/extract",
    response_model=ExtractionResponse,
    dependencies=[Depends(extract_rate_limit)],
)
async def trigger_nlp_extraction(
    meeting_id: str,
    user: UserIdentity = Depends(require_member),
) -> ExtractionResponse:
    """Re-run NLP extraction on the stored transcript.

    Keeps fact IDs and lifecycle state, refreshes evidence and embeddings, and re-runs the
    cross-meeting reconciliation for this meeting.
    """
    from apps.api.providers import build_embedder

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await _require_meeting(repo, meeting_id, user.org_id)
        segments = await repo.get_transcript_segments(meeting_id)
        if not segments:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot run extraction: Meeting '{meeting_id}' has no transcript segments.",
            )

    results = await NLPExtractionPipeline().process_transcript(
        meeting_id=meeting_id,
        segments=segments,
        meeting_date=meeting.meeting_date,
    )
    vectors = await build_embedder().embed([s.text for s in segments])

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await repo.save_nlp_extraction_results(meeting_id, results)
        await repo.save_embeddings(
            meeting_id,
            [("segment", s.segment_id, s.text, v) for s, v in zip(segments, vectors, strict=False)],
        )
        await repo.save_evidence_records(meeting_id, results.evidence)
        await TemporalIntelligenceEngine(session, org_id=user.org_id).reconcile_meeting_lifecycle(
            meeting_id
        )

    return ExtractionResponse(
        meeting_id=meeting_id,
        entities_count=len(results.entities),
        topics_count=len(results.topics),
        decisions_count=len(results.decisions),
        commitments_count=len(results.commitments),
        issues_count=len(results.issues),
        events_count=len(results.events),
        relations_count=len(results.relations),
    )

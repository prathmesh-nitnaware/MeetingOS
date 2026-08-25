import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from apps.api.config import settings
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
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
from pydantic import BaseModel, Field
from workers.tasks.ingestion import run_ingestion_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["Meetings"])


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
    speakers_count: int
    segments_count: int
    metadata: MeetingMetadata
    created_at: datetime
    updated_at: datetime


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


@router.post("", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_and_upload_meeting(
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(min_length=1, max_length=500)],
    meeting_date: Annotated[str | None, Form()] = None,
    participants: Annotated[str | None, Form()] = None,
    async_processing: Annotated[bool, Form()] = False,
) -> MeetingCreateResponse:
    """Upload a meeting audio/video/text file, create a meeting record, and trigger ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    try:
        source_type = validate_file_extension(file.filename)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meeting_id = f"meet-{uuid4()}"
    job_id = f"job-{uuid4()}"

    # Parse meeting date
    parsed_date = datetime.now(UTC)
    if meeting_date:
        try:
            parsed_date = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_date = datetime.strptime(meeting_date, "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid meeting_date format '{meeting_date}'. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).",
                ) from exc

    # Parse participants JSON if provided
    parsed_participants: list[Participant] = []
    if participants:
        try:
            raw_parts = json.loads(participants)
            if isinstance(raw_parts, list):
                for p in raw_parts:
                    if isinstance(p, str):
                        parsed_participants.append(Participant(canonical_name=p))
                    elif isinstance(p, dict) and "canonical_name" in p:
                        parsed_participants.append(Participant(**p))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid participants JSON format: {exc}"
            ) from exc

    # Save uploaded file
    storage_dir = Path(settings.upload_storage_dir)
    file_ext = Path(file.filename).suffix.lower()
    dest_path = storage_dir / f"{meeting_id}{file_ext}"

    try:
        file_size = save_upload_file(file.file, dest_path, max_size_mb=settings.max_upload_size_mb)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Assemble initial CMF meeting object
    meeting = Meeting(
        meeting_id=meeting_id,
        title=title,
        meeting_date=parsed_date,
        source_type=source_type,
        processing_status=ProcessingStatus.QUEUED,
        participants=parsed_participants,
        metadata=MeetingMetadata(
            source_filename=file.filename,
            file_size_bytes=file_size,
        ),
    )

    # Persist meeting and job in DB
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await repo.create_meeting(meeting)
        await repo.create_job(job_id=job_id, meeting_id=meeting_id, stage="queued")

    # Ingestion execution
    if async_processing:
        # Launch asynchronous background task
        _task = asyncio.create_task(
            run_ingestion_pipeline(
                meeting_id=meeting_id,
                job_id=job_id,
                file_path_str=str(dest_path),
                source_type_str=str(source_type),
                database_url=settings.database_url,
                asr_provider_name=settings.asr_provider,
                diarizer_provider_name=settings.diarizer_provider,
            )
        )
        _ = _task
    else:
        # Process synchronously for immediate completion / testing
        await run_ingestion_pipeline(
            meeting_id=meeting_id,
            job_id=job_id,
            file_path_str=str(dest_path),
            source_type_str=str(source_type),
            database_url=settings.database_url,
            asr_provider_name=settings.asr_provider,
            diarizer_provider_name=settings.diarizer_provider,
        )

    return MeetingCreateResponse(
        meeting_id=meeting_id,
        job_id=job_id,
        processing_status=ProcessingStatus.QUEUED
        if async_processing
        else ProcessingStatus.SUCCEEDED,
        title=title,
    )


@router.get("", response_model=list[MeetingSummaryResponse])
async def list_meetings(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MeetingSummaryResponse]:
    """List all ingested meetings ordered by date descending."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meetings = await repo.list_meetings(limit=limit, offset=offset)

    return [
        MeetingSummaryResponse(
            meeting_id=m.meeting_id,
            title=m.title,
            meeting_date=m.meeting_date,
            duration_seconds=m.duration_seconds,
            source_type=m.source_type,
            processing_status=m.processing_status,
            participant_count=len(m.participants),
            segment_count=len(m.segments),
            created_at=m.created_at,
        )
        for m in meetings
    ]


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(meeting_id: str) -> MeetingDetailResponse:
    """Get full metadata, processing status, and participants for a specific meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=404,
            detail=f"Meeting with ID '{meeting_id}' not found.",
        )

    return MeetingDetailResponse(
        meeting_id=meeting.meeting_id,
        title=meeting.title,
        meeting_date=meeting.meeting_date,
        duration_seconds=meeting.duration_seconds,
        source_type=meeting.source_type,
        processing_status=meeting.processing_status,
        participants=meeting.participants,
        speakers_count=len(meeting.speakers),
        segments_count=len(meeting.segments),
        metadata=meeting.metadata,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_meeting_transcript(meeting_id: str) -> TranscriptResponse:
    """Get all timestamped transcript segments for a meeting ordered by sequence."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail=f"Meeting with ID '{meeting_id}' not found.",
            )
        segments = await repo.get_transcript_segments(meeting_id)

    return TranscriptResponse(
        meeting_id=meeting_id,
        segments_count=len(segments),
        segments=segments,
    )


# --------------------------------------------------------------------------
# Phase 2: NLP Facts Sub-resource Endpoints
# --------------------------------------------------------------------------


@router.get("/{meeting_id}/entities", response_model=list[ExtractedEntity])
async def get_meeting_entities(meeting_id: str) -> list[ExtractedEntity]:
    """Retrieve all named and domain entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_entities(meeting_id)


@router.get("/{meeting_id}/topics", response_model=list[str])
async def get_meeting_topics(meeting_id: str) -> list[str]:
    """Retrieve discussion topics extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_topics(meeting_id)


@router.get("/{meeting_id}/decisions", response_model=list[ExtractedDecision])
async def get_meeting_decisions(meeting_id: str) -> list[ExtractedDecision]:
    """Retrieve decisions extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_decisions(meeting_id)


@router.get("/{meeting_id}/actions", response_model=list[ExtractedCommitment])
async def get_meeting_actions(meeting_id: str) -> list[ExtractedCommitment]:
    """Retrieve action items and commitments extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_actions(meeting_id)


@router.get("/{meeting_id}/issues", response_model=list[ExtractedIssue])
async def get_meeting_issues(meeting_id: str) -> list[ExtractedIssue]:
    """Retrieve issues and problems extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_issues(meeting_id)


@router.get("/{meeting_id}/timeline", response_model=list[ExtractedEvent])
async def get_meeting_timeline(meeting_id: str) -> list[ExtractedEvent]:
    """Retrieve chronological lifecycle events extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_timeline(meeting_id)


@router.get("/{meeting_id}/relations", response_model=list[ExtractedRelation])
async def get_meeting_relations(meeting_id: str) -> list[ExtractedRelation]:
    """Retrieve typed relations between entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_relations(meeting_id)


@router.post("/{meeting_id}/extract", response_model=ExtractionResponse)
async def trigger_nlp_extraction(meeting_id: str) -> ExtractionResponse:
    """Trigger on-demand NLP extraction on existing transcript segments."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        segments = await repo.get_transcript_segments(meeting_id)
        if not segments:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot run extraction: Meeting '{meeting_id}' has no transcript segments.",
            )

    nlp_pipe = NLPExtractionPipeline()
    results = await nlp_pipe.process_transcript(
        meeting_id=meeting_id,
        segments=segments,
        meeting_date=meeting.meeting_date,
    )

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await repo.save_nlp_extraction_results(meeting_id, results)

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

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
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
    TranscriptSegment,
)
from packages.ingestion.validator import (
    FileValidationError,
    save_upload_file,
    validate_file_extension,
)
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionPipeline, NLPExtractionResult
from packages.nlp.text_analyzer import analyze_text_intelligence, parse_text_to_segments
from pydantic import BaseModel, Field
from workers.tasks.ingestion import run_ingestion_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["Meetings"])


class MeetingCreateTextRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    meeting_date: datetime | None = None
    participants: list[str | dict[str, Any]] = Field(default_factory=list)
    content_type: str = "transcript"  # "transcript" | "notes" | "discussion" | "import"
    content: str = ""
    project_id: str | None = None
    auto_analyze: bool = True


class MeetingUpdateRequest(BaseModel):
    title: str | None = None
    meeting_date: datetime | None = None
    content_type: str | None = None
    content: str | None = None
    summary: str | None = None
    key_points: list[str] | None = None
    project_id: str | None = None
    participants: list[str | dict[str, Any]] | None = None


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    job_id: str
    processing_status: ProcessingStatus
    title: str
    summary: str | None = None
    decisions_count: int = 0
    actions_count: int = 0
    topics_count: int = 0
    message: str = "Meeting created and processed successfully."


class MeetingSummaryResponse(BaseModel):
    meeting_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None = None
    source_type: SourceType
    content_type: str = "transcript"
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    decisions_count: int = 0
    actions_count: int = 0
    participant_count: int
    segment_count: int
    project_id: str | None = None
    processing_status: ProcessingStatus
    created_at: datetime


class MeetingDetailResponse(BaseModel):
    meeting_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None = None
    source_type: SourceType
    content_type: str = "transcript"
    content: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    project_id: str | None = None
    processing_status: ProcessingStatus
    participants: list[Participant] = Field(default_factory=list)
    speakers_count: int = 0
    segments_count: int = 0
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    action_items: list[ExtractedCommitment] = Field(default_factory=list)
    metadata: MeetingMetadata
    created_at: datetime
    updated_at: datetime


class TranscriptResponse(BaseModel):
    meeting_id: str
    segments_count: int
    segments: list[TranscriptSegment]


class ExtractionResponse(BaseModel):
    meeting_id: str
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    action_items: list[ExtractedCommitment] = Field(default_factory=list)
    entities_count: int = 0
    topics_count: int = 0
    decisions_count: int = 0
    commitments_count: int = 0
    issues_count: int = 0
    events_count: int = 0
    relations_count: int = 0
    message: str = "Meeting analyzed and structured intelligence persisted successfully."


@router.post("/create-text", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/text", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_text_meeting(
    req: MeetingCreateTextRequest,
    user: UserIdentity = Depends(require_member),
) -> MeetingCreateResponse:
    """Create a new text-first meeting from transcript, notes, or discussion text with instant AI analysis."""
    meeting_id = f"meet-{uuid4()}"
    job_id = f"job-{uuid4()}"
    m_date = req.meeting_date or datetime.now(UTC)

    # Parse participants
    parsed_participants: list[Participant] = []
    for p in req.participants:
        if isinstance(p, str):
            parsed_participants.append(Participant(canonical_name=p.strip()))
        elif isinstance(p, dict) and "canonical_name" in p:
            parsed_participants.append(Participant(**p))

    # Parse text into segments & speakers
    segments, speakers = parse_text_to_segments(req.content, content_type=req.content_type)

    summary = ""
    key_points: list[str] = []
    topics: list[str] = []
    decisions: list[ExtractedDecision] = []
    action_items: list[ExtractedCommitment] = []

    if req.auto_analyze and req.content.strip():
        analysis = analyze_text_intelligence(
            title=req.title,
            content=req.content,
            meeting_date=m_date,
            existing_participants=parsed_participants,
            meeting_id=meeting_id,
        )
        summary = analysis.summary
        key_points = analysis.key_points
        topics = analysis.topics
        decisions = analysis.decisions
        action_items = analysis.action_items
        parsed_participants = analysis.participants

    meeting = Meeting(
        meeting_id=meeting_id,
        title=req.title,
        meeting_date=m_date,
        source_type=SourceType.TEXT_TRANSCRIPT,
        processing_status=ProcessingStatus.SUCCEEDED,
        content_type=req.content_type,
        content=req.content,
        summary=summary,
        key_points=key_points,
        project_id=req.project_id,
        participants=parsed_participants,
        speakers=speakers,
        segments=segments,
        metadata=MeetingMetadata(
            content_type=req.content_type,
            project_id=req.project_id,
        ),
    )

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        await repo.create_meeting(meeting, org_id=user.org_id)
        await repo.create_job(job_id=job_id, meeting_id=meeting_id, stage="completed")

        if req.auto_analyze and (decisions or action_items or topics):
            nlp_res = NLPExtractionResult(
                meeting_id=meeting_id,
                topics=topics,
                decisions=decisions,
                commitments=action_items,
                actions=action_items,
            )
            await repo.save_nlp_extraction_results(meeting_id, nlp_res)

        await session.commit()

    return MeetingCreateResponse(
        meeting_id=meeting_id,
        job_id=job_id,
        processing_status=ProcessingStatus.SUCCEEDED,
        title=req.title,
        summary=summary,
        decisions_count=len(decisions),
        actions_count=len(action_items),
        topics_count=len(topics),
        message="Text meeting created and analyzed successfully.",
    )


@router.post("", response_model=MeetingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    request: Request,
    user: UserIdentity = Depends(require_member),
) -> MeetingCreateResponse:
    """Create a meeting. Supports JSON body for text meetings, and form-data for legacy file imports."""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        req = MeetingCreateTextRequest(**body)
        return await create_text_meeting(req, user=user)

    # Handle multipart form data
    form = await request.form()
    file = form.get("file")
    title = form.get("title")
    meeting_date = form.get("meeting_date")
    participants = form.get("participants")
    async_processing = str(form.get("async_processing", "false")).lower() == "true"
    content = str(form.get("content", ""))

    if not title:
        raise HTTPException(status_code=400, detail="Meeting title is required.")

    meeting_id = f"meet-{uuid4()}"
    job_id = f"job-{uuid4()}"

    # Parse meeting date
    parsed_date = datetime.now(UTC)
    if meeting_date:
        try:
            parsed_date = datetime.fromisoformat(str(meeting_date).replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_date = datetime.strptime(str(meeting_date), "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid meeting_date format '{meeting_date}'. Expected ISO format.",
                ) from exc

    # Parse participants
    parsed_participants: list[Participant] = []
    if participants:
        try:
            raw_parts = json.loads(str(participants))
            if isinstance(raw_parts, list):
                for p in raw_parts:
                    if isinstance(p, str):
                        parsed_participants.append(Participant(canonical_name=p))
                    elif isinstance(p, dict) and "canonical_name" in p:
                        parsed_participants.append(Participant(**p))
        except (json.JSONDecodeError, ValueError):
            pass

    # If an uploaded file is present (e.g. srt or legacy audio)
    if file and hasattr(file, "filename") and file.filename:
        try:
            source_type = validate_file_extension(file.filename)
        except FileValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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
            title=str(title),
            meeting_date=parsed_date,
            source_type=source_type,
            processing_status=ProcessingStatus.QUEUED,
            participants=parsed_participants,
            metadata=MeetingMetadata(
                source_filename=file.filename,
                file_size_bytes=file_size,
            ),
        )

        async with get_db_session(settings.database_url) as session:
            repo = MeetingRepository(session)
            await repo.create_meeting(meeting, org_id=user.org_id)
            await repo.create_job(job_id=job_id, meeting_id=meeting_id, stage="queued")
            await session.commit()

        if async_processing:
            _ = asyncio.create_task(
                run_ingestion_pipeline(
                    meeting_id=meeting_id,
                    job_id=job_id,
                    file_path_str=str(dest_path),
                    source_type_str=str(source_type),
                    database_url=settings.database_url,
                    org_id=user.org_id,
                    asr_provider_name=settings.asr_provider,
                    diarizer_provider_name=settings.diarizer_provider,
                )
            )
        else:
            await run_ingestion_pipeline(
                meeting_id=meeting_id,
                job_id=job_id,
                file_path_str=str(dest_path),
                source_type_str=str(source_type),
                database_url=settings.database_url,
                org_id=user.org_id,
                asr_provider_name=settings.asr_provider,
                diarizer_provider_name=settings.diarizer_provider,
            )

        return MeetingCreateResponse(
            meeting_id=meeting_id,
            job_id=job_id,
            processing_status=ProcessingStatus.QUEUED if async_processing else ProcessingStatus.SUCCEEDED,
            title=str(title),
        )

    # Form text creation fallback
    req = MeetingCreateTextRequest(
        title=str(title),
        meeting_date=parsed_date,
        participants=[p.canonical_name for p in parsed_participants],
        content=content,
        auto_analyze=True,
    )
    return await create_text_meeting(req, user=user)


@router.post("/{meeting_id}/analyze", response_model=ExtractionResponse)
async def analyze_meeting(
    meeting_id: str,
    user: UserIdentity = Depends(require_member),
) -> ExtractionResponse:
    """Analyze meeting transcript or notes and extract structured executive summary, key points, topics, decisions, and action items."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

        # Determine content
        content = meeting.content
        if not content:
            segments = await repo.get_transcript_segments(meeting_id)
            if segments:
                content = "\n".join(s.text for s in segments)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot analyze meeting: Meeting content and transcript are empty.",
                )

        analysis = analyze_text_intelligence(
            title=meeting.title,
            content=content,
            meeting_date=meeting.meeting_date,
            existing_participants=meeting.participants,
            meeting_id=meeting_id,
        )

        # Update meeting summary and key points
        await repo.update_meeting(
            meeting_id=meeting_id,
            org_id=user.org_id,
            summary=analysis.summary,
            key_points=analysis.key_points,
            participants=analysis.participants,
        )

        # Persist facts
        nlp_res = NLPExtractionResult(
            meeting_id=meeting_id,
            topics=analysis.topics,
            decisions=analysis.decisions,
            commitments=analysis.action_items,
            actions=analysis.action_items,
        )
        await repo.save_nlp_extraction_results(meeting_id, nlp_res)
        await session.commit()

    return ExtractionResponse(
        meeting_id=meeting_id,
        summary=analysis.summary,
        key_points=analysis.key_points,
        topics=analysis.topics,
        decisions=analysis.decisions,
        action_items=analysis.action_items,
        topics_count=len(analysis.topics),
        decisions_count=len(analysis.decisions),
        commitments_count=len(analysis.action_items),
        message="Meeting analyzed and structured intelligence persisted successfully.",
    )


@router.patch("/{meeting_id}", response_model=MeetingDetailResponse)
async def update_meeting_details(
    meeting_id: str,
    req: MeetingUpdateRequest,
    user: UserIdentity = Depends(require_member),
) -> MeetingDetailResponse:
    """Update meeting title, date, content, summary, or participants."""
    parsed_participants: list[Participant] | None = None
    if req.participants is not None:
        parsed_participants = []
        for p in req.participants:
            if isinstance(p, str):
                parsed_participants.append(Participant(canonical_name=p.strip()))
            elif isinstance(p, dict) and "canonical_name" in p:
                parsed_participants.append(Participant(**p))

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        updated = await repo.update_meeting(
            meeting_id=meeting_id,
            org_id=user.org_id,
            title=req.title,
            meeting_date=req.meeting_date,
            content_type=req.content_type,
            content=req.content,
            summary=req.summary,
            key_points=req.key_points,
            project_id=req.project_id,
            participants=parsed_participants,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

        # Re-parse segments if content was updated
        if req.content is not None:
            segments, speakers = parse_text_to_segments(req.content, content_type=updated.content_type)
            await repo.save_transcript_segments(meeting_id, segments, speakers)

        await session.commit()

        # Fetch full details
        decisions = await repo.get_meeting_decisions(meeting_id)
        actions = await repo.get_meeting_actions(meeting_id)
        topics = await repo.get_meeting_topics(meeting_id)
        segments = await repo.get_transcript_segments(meeting_id)

    return MeetingDetailResponse(
        meeting_id=updated.meeting_id,
        title=updated.title,
        meeting_date=updated.meeting_date,
        duration_seconds=updated.duration_seconds,
        source_type=updated.source_type,
        content_type=updated.content_type,
        content=updated.content,
        summary=updated.summary,
        key_points=updated.key_points,
        topics=topics,
        processing_status=updated.processing_status,
        participants=updated.participants,
        speakers_count=len(updated.speakers),
        segments_count=len(segments),
        decisions=decisions,
        action_items=actions,
        metadata=updated.metadata,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.get("", response_model=list[MeetingSummaryResponse])
async def list_meetings(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    topic: Annotated[str | None, Query()] = None,
    project_id: Annotated[str | None, Query()] = None,
    user: UserIdentity = Depends(require_viewer),
) -> list[MeetingSummaryResponse]:
    """List all meetings with summary preview, topic tags, and decision/action counts."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meetings = await repo.list_meetings(org_id=user.org_id, limit=limit, offset=offset)

        summaries: list[MeetingSummaryResponse] = []
        for m in meetings:
            if project_id and m.project_id != project_id:
                continue
            topics = await repo.get_meeting_topics(m.meeting_id)
            if topic and not any(topic.lower() in t.lower() for t in topics):
                continue
            decisions = await repo.get_meeting_decisions(m.meeting_id)
            actions = await repo.get_meeting_actions(m.meeting_id)

            summaries.append(
                MeetingSummaryResponse(
                    meeting_id=m.meeting_id,
                    title=m.title,
                    meeting_date=m.meeting_date,
                    duration_seconds=m.duration_seconds,
                    source_type=m.source_type,
                    content_type=m.content_type,
                    summary=m.summary,
                    key_points=m.key_points,
                    topics=topics,
                    decisions_count=len(decisions),
                    actions_count=len(actions),
                    participant_count=len(m.participants),
                    segment_count=len(m.segments),
                    project_id=m.project_id,
                    processing_status=m.processing_status,
                    created_at=m.created_at,
                )
            )

    return summaries


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> MeetingDetailResponse:
    """Get full details, content, summary, key points, decisions, and action items for a meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting with ID '{meeting_id}' not found.")

        decisions = await repo.get_meeting_decisions(meeting_id)
        actions = await repo.get_meeting_actions(meeting_id)
        topics = await repo.get_meeting_topics(meeting_id)
        segments = await repo.get_transcript_segments(meeting_id)

    return MeetingDetailResponse(
        meeting_id=meeting.meeting_id,
        title=meeting.title,
        meeting_date=meeting.meeting_date,
        duration_seconds=meeting.duration_seconds,
        source_type=meeting.source_type,
        content_type=meeting.content_type,
        content=meeting.content,
        summary=meeting.summary,
        key_points=meeting.key_points,
        topics=topics,
        project_id=meeting.project_id,
        processing_status=meeting.processing_status,
        participants=meeting.participants,
        speakers_count=len(meeting.speakers),
        segments_count=len(segments),
        decisions=decisions,
        action_items=actions,
        metadata=meeting.metadata,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.patch("/{meeting_id}", response_model=MeetingDetailResponse)
async def update_meeting_endpoint(
    meeting_id: str,
    req: MeetingUpdateRequest,
    user: UserIdentity = Depends(require_member),
) -> MeetingDetailResponse:
    """Update meeting title, date, content, summary, key points, or project assignment."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

        parts: list[Participant] | None = None
        if req.participants is not None:
            parts = []
            for p in req.participants:
                if isinstance(p, str):
                    parts.append(Participant(canonical_name=p.strip()))
                elif isinstance(p, dict) and "canonical_name" in p:
                    parts.append(Participant(**p))

        updated = await repo.update_meeting(
            meeting_id=meeting_id,
            org_id=user.org_id,
            title=req.title,
            meeting_date=req.meeting_date,
            content_type=req.content_type,
            content=req.content,
            summary=req.summary,
            key_points=req.key_points,
            project_id=req.project_id,
            participants=parts,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

        # If content changed, update segments
        if req.content is not None and req.content.strip():
            segments, speakers = parse_text_to_segments(req.content, content_type=req.content_type or updated.content_type)
            await repo.save_transcript_segments(meeting_id, segments, speakers)

        await session.commit()

        decisions = await repo.get_meeting_decisions(meeting_id)
        actions = await repo.get_meeting_actions(meeting_id)
        topics = await repo.get_meeting_topics(meeting_id)
        segments = await repo.get_transcript_segments(meeting_id)

    return MeetingDetailResponse(
        meeting_id=updated.meeting_id,
        title=updated.title,
        meeting_date=updated.meeting_date,
        duration_seconds=updated.duration_seconds,
        source_type=updated.source_type,
        content_type=updated.content_type,
        content=updated.content,
        summary=updated.summary,
        key_points=updated.key_points,
        topics=topics,
        project_id=updated.project_id,
        processing_status=updated.processing_status,
        participants=updated.participants,
        speakers_count=len(updated.speakers),
        segments_count=len(segments),
        decisions=decisions,
        action_items=actions,
        metadata=updated.metadata,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post("/{meeting_id}/analyze", response_model=ExtractionResponse)
async def reanalyze_meeting_intelligence(
    meeting_id: str,
    user: UserIdentity = Depends(require_member),
) -> ExtractionResponse:
    """Re-analyze meeting content using the zero-hallucination NLP and evidence validation pipeline."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        if not meeting.content or not meeting.content.strip():
            raise HTTPException(status_code=400, detail="Cannot analyze meeting: content is empty.")

        analysis = analyze_text_intelligence(
            title=meeting.title,
            content=meeting.content,
            meeting_date=meeting.meeting_date,
            existing_participants=meeting.participants,
            meeting_id=meeting_id,
        )

        # Update meeting summary, key points, participants
        await repo.update_meeting(
            meeting_id=meeting_id,
            org_id=user.org_id,
            summary=analysis.summary,
            key_points=analysis.key_points,
            participants=analysis.participants,
        )

        nlp_res = NLPExtractionResult(
            meeting_id=meeting_id,
            topics=analysis.topics,
            decisions=analysis.decisions,
            commitments=analysis.action_items,
            actions=analysis.action_items,
        )
        await repo.save_nlp_extraction_results(meeting_id, nlp_res)
        await session.commit()

    return ExtractionResponse(
        meeting_id=meeting_id,
        summary=analysis.summary,
        key_points=analysis.key_points,
        topics=analysis.topics,
        decisions=analysis.decisions,
        action_items=analysis.action_items,
        topics_count=len(analysis.topics),
        decisions_count=len(analysis.decisions),
        commitments_count=len(analysis.action_items),
        message="Meeting re-analyzed with zero-hallucination validation successfully.",
    )


@router.get("/{meeting_id}/evidence", response_model=dict[str, Any])
async def get_meeting_evidence_and_spans(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve full source evidence mapping for decisions, action items, and topics."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

        decisions = await repo.get_meeting_decisions(meeting_id)
        actions = await repo.get_meeting_actions(meeting_id)
        topics = await repo.get_meeting_topics(meeting_id)
        segments = await repo.get_transcript_segments(meeting_id)

    return {
        "meeting_id": meeting_id,
        "title": meeting.title,
        "content": meeting.content,
        "segments": [s.model_dump() for s in segments],
        "decisions_evidence": [
            {
                "decision_id": d.decision_id,
                "subject": d.subject,
                "confidence": d.confidence,
                "source_text": d.source_text,
                "source_start": d.source_start,
                "source_end": d.source_end,
                "review_status": d.review_status,
            }
            for d in decisions
        ],
        "actions_evidence": [
            {
                "commitment_id": a.commitment_id,
                "task": a.task,
                "owner": a.owner_id,
                "due_date": a.due_date_str,
                "confidence": a.confidence,
                "source_text": a.source_text,
                "source_start": a.source_start,
                "source_end": a.source_end,
                "review_status": a.review_status,
            }
            for a in actions
        ],
    }


@router.patch("/{meeting_id}/decisions/{decision_id}/review", response_model=dict[str, Any])
async def update_meeting_decision_review(
    meeting_id: str,
    decision_id: str,
    review_status: Annotated[str, Query(description="Review status: confirmed, edited, rejected, needs_review")],
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Update human review status for an extracted decision."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        updated = await repo.update_decision(
            decision_id=decision_id,
            org_id=user.org_id,
            review_status=review_status,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found.")
        await session.commit()
        return updated


@router.patch("/{meeting_id}/actions/{commitment_id}/review", response_model=dict[str, Any])
async def update_meeting_action_review(
    meeting_id: str,
    commitment_id: str,
    review_status: Annotated[str, Query(description="Review status: confirmed, edited, rejected, needs_review")],
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Update human review status for an extracted action item."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        updated = await repo.update_action_item(
            commitment_id=commitment_id,
            org_id=user.org_id,
            review_status=review_status,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Action item '{commitment_id}' not found.")
        await session.commit()
        return updated


@router.delete("/{meeting_id}", response_model=dict[str, Any])
async def delete_meeting(
    meeting_id: str,
    hard_delete: bool = Query(default=False, description="Permanently delete rather than soft-deleting"),
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Delete a meeting. Defaults to soft deletion for safety."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        if hard_delete:
            success = await repo.hard_delete_meeting(meeting_id=meeting_id, org_id=user.org_id)
        else:
            success = await repo.soft_delete_meeting(
                meeting_id=meeting_id, actor_id=user.user_id, org_id=user.org_id
            )
        if not success:
            raise HTTPException(status_code=404, detail=f"Meeting with ID '{meeting_id}' not found.")
        await session.commit()
        return {
            "status": "succeeded",
            "meeting_id": meeting_id,
            "deletion_type": "hard_delete" if hard_delete else "soft_delete",
        }


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_meeting_transcript(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> TranscriptResponse:
    """Get all transcript segments for a meeting ordered by sequence."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting with ID '{meeting_id}' not found.")
        segments = await repo.get_transcript_segments(meeting_id)

    return TranscriptResponse(
        meeting_id=meeting_id,
        segments_count=len(segments),
        segments=segments,
    )


@router.get("/{meeting_id}/entities", response_model=list[ExtractedEntity])
async def get_meeting_entities(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedEntity]:
    """Retrieve named entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_entities(meeting_id)


@router.get("/{meeting_id}/topics", response_model=list[str])
async def get_meeting_topics(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[str]:
    """Retrieve discussion topics extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_topics(meeting_id)


@router.get("/{meeting_id}/decisions", response_model=list[ExtractedDecision])
async def get_meeting_decisions(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedDecision]:
    """Retrieve decisions extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_decisions(meeting_id)


@router.get("/{meeting_id}/actions", response_model=list[ExtractedCommitment])
async def get_meeting_actions(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedCommitment]:
    """Retrieve action items and commitments extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_actions(meeting_id)


@router.get("/{meeting_id}/issues", response_model=list[ExtractedIssue])
async def get_meeting_issues(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedIssue]:
    """Retrieve issues extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_issues(meeting_id)


@router.get("/{meeting_id}/timeline", response_model=list[ExtractedEvent])
async def get_meeting_timeline(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedEvent]:
    """Retrieve chronological timeline events extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_timeline(meeting_id)


@router.get("/{meeting_id}/relations", response_model=list[ExtractedRelation])
async def get_meeting_relations(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[ExtractedRelation]:
    """Retrieve typed relations between entities extracted from the meeting."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")
        return await repo.get_meeting_relations(meeting_id)


@router.post("/{meeting_id}/extract", response_model=ExtractionResponse)
async def trigger_nlp_extraction(
    meeting_id: str,
    user: UserIdentity = Depends(require_member),
) -> ExtractionResponse:
    """Trigger NLP extraction pipeline on existing transcript segments."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id, org_id=user.org_id)
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
        await session.commit()

    return ExtractionResponse(
        meeting_id=meeting_id,
        entities_count=len(results.entities),
        topics_count=len(results.topics),
        decisions_count=len(results.decisions),
        commitments_count=len(results.commitments),
        issues_count=len(results.issues),
        events_count=len(results.events),
        relations_count=len(results.relations),
        message="NLP facts extracted and persisted successfully.",
    )


# --------------------------------------------------------------------------
# Legacy Audio Retrieval (Isolated & Deprecated)
# --------------------------------------------------------------------------

@router.get("/{meeting_id}/audio", deprecated=True)
async def get_meeting_audio_legacy(
    meeting_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> FileResponse:
    """[DEPRECATED] Download legacy audio file if one was historically uploaded."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        meeting = await repo.get_meeting(meeting_id=meeting_id, org_id=user.org_id)
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found.")

    storage_base = Path(settings.upload_storage_dir).resolve()
    tenant_dir = (storage_base / "orgs" / user.org_id / "meetings" / meeting_id).resolve()

    try:
        tenant_dir.relative_to(storage_base)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: invalid storage path traversal.")

    if not tenant_dir.exists() or not tenant_dir.is_dir():
        raise HTTPException(status_code=404, detail="Audio file not found on storage.")

    audio_files = list(tenant_dir.glob("audio.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found.")

    target_file = audio_files[0].resolve()
    return FileResponse(
        path=target_file,
        media_type="audio/wav",
        filename=f"{meeting.title or meeting_id}.wav",
    )

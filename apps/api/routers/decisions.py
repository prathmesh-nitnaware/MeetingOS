from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.common.enums import DecisionStatus
from packages.memory.database import get_db_session
from packages.memory.models import DecisionModel, MeetingModel
from packages.memory.repository import MeetingRepository
from pydantic import BaseModel
from sqlalchemy import select

router = APIRouter(prefix="/decisions", tags=["Decisions"])


class DecisionUpdateRequest(BaseModel):
    status: str | None = None
    title: str | None = None
    subject: str | None = None
    context: str | None = None
    rationale: str | None = None
    review_status: str | None = None


class DecisionCreateRequest(BaseModel):
    meeting_id: str
    title: str
    subject: str | None = None
    status: str = "Approved"
    context: str | None = None
    rationale: str | None = None
    confidence: float = 1.0


@router.get("", response_model=list[dict[str, Any]])
async def list_decisions(
    status: Annotated[str | None, Query(description="Filter by decision status (e.g. Approved, Proposed, Modified, Reversed)")] = None,
    meeting_id: Annotated[str | None, Query(description="Filter by source meeting ID")] = None,
    project_id: Annotated[str | None, Query(description="Filter by project ID")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List organizational decisions across all meetings in the authenticated organization."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.list_all_decisions(
            org_id=user.org_id,
            status=status,
            meeting_id=meeting_id,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )


@router.patch("/{decision_id}", response_model=dict[str, Any])
async def update_decision(
    decision_id: str,
    req: DecisionUpdateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Update status, title, context, rationale, or review status of a decision."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        item = await repo.update_decision(
            decision_id=decision_id,
            org_id=user.org_id,
            status=req.status,
            title=req.title,
            subject=req.subject,
            context=req.context,
            rationale=req.rationale,
            review_status=req.review_status,
        )
        if not item:
            raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found.")
        await session.commit()
        return item


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_decision(
    req: DecisionCreateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Create a new decision record associated with a meeting."""
    async with get_db_session(settings.database_url) as session:
        m_stmt = select(MeetingModel).where(
            MeetingModel.id == req.meeting_id,
            MeetingModel.org_id == user.org_id,
            MeetingModel.deleted_at.is_(None),
        )
        m_res = await session.execute(m_stmt)
        meeting = m_res.scalar_one_or_none()
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{req.meeting_id}' not found.")

        dec_id = f"dec-{uuid4()}"
        new_dec = DecisionModel(
            id=dec_id,
            meeting_id=req.meeting_id,
            title=req.title,
            subject=req.subject or req.title,
            status=req.status,
            context=req.context,
            rationale=req.rationale or f"Agreed during {meeting.title}",
            confidence=req.confidence,
            created_at=datetime.now(UTC),
        )
        session.add(new_dec)
        await session.commit()

        return {
            "decision_id": dec_id,
            "id": dec_id,
            "title": req.title,
            "subject": req.subject or req.title,
            "status": req.status,
            "context": req.context,
            "rationale": req.rationale,
            "confidence": req.confidence,
            "meeting_id": req.meeting_id,
            "meeting_title": meeting.title,
            "meeting_date": meeting.meeting_date.isoformat(),
        }

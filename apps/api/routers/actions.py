from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.common.enums import CommitmentStatus
from packages.common.models import ExtractedCommitment
from packages.memory.database import get_db_session
from packages.memory.models import CommitmentModel, MeetingModel
from packages.memory.repository import MeetingRepository
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/action-items", tags=["Action Items"])


class ActionItemUpdateRequest(BaseModel):
    status: str | None = None
    task: str | None = None
    description: str | None = None
    owner_id: str | None = None
    priority: str | None = None
    due_date_str: str | None = None
    review_status: str | None = None


class ActionItemCreateRequest(BaseModel):
    meeting_id: str
    task: str
    description: str | None = None
    owner_id: str = "Unassigned"
    priority: str = "medium"
    due_date_str: str = "Not specified"
    status: str = "In Progress"


@router.get("", response_model=list[dict[str, Any]])
async def list_action_items(
    status: Annotated[str | None, Query(description="Filter by status (e.g. Open, In Progress, Completed)")] = None,
    owner: Annotated[str | None, Query(description="Filter by owner name")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority (low, medium, high)")] = None,
    meeting_id: Annotated[str | None, Query(description="Filter by source meeting ID")] = None,
    project_id: Annotated[str | None, Query(description="Filter by project ID")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List action items across all meetings in the authenticated organization."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.list_all_action_items(
            org_id=user.org_id,
            status=status,
            owner=owner,
            priority=priority,
            meeting_id=meeting_id,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )


@router.patch("/{commitment_id}", response_model=dict[str, Any])
async def update_action_item(
    commitment_id: str,
    req: ActionItemUpdateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Update status, assignment, priority, due date, or review status of an action item."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        item = await repo.update_action_item(
            commitment_id=commitment_id,
            org_id=user.org_id,
            status=req.status,
            task=req.task,
            description=req.description,
            owner_id=req.owner_id,
            priority=req.priority,
            due_date_str=req.due_date_str,
            review_status=req.review_status,
        )
        if not item:
            raise HTTPException(status_code=404, detail=f"Action item '{commitment_id}' not found.")
        await session.commit()
        return item


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_action_item(
    req: ActionItemCreateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Create a new action item associated with a meeting."""
    async with get_db_session(settings.database_url) as session:
        # Verify meeting belongs to user's org
        m_stmt = select(MeetingModel).where(
            MeetingModel.id == req.meeting_id,
            MeetingModel.org_id == user.org_id,
            MeetingModel.deleted_at.is_(None),
        )
        m_res = await session.execute(m_stmt)
        meeting = m_res.scalar_one_or_none()
        if not meeting:
            raise HTTPException(status_code=404, detail=f"Meeting '{req.meeting_id}' not found.")

        item_id = f"com-{uuid4()}"
        new_item = CommitmentModel(
            id=item_id,
            meeting_id=req.meeting_id,
            task=req.task,
            description=req.description or req.task,
            owner_id=req.owner_id,
            status=req.status,
            priority=req.priority,
            due_date_str=req.due_date_str,
        )
        session.add(new_item)
        await session.commit()

        return {
            "commitment_id": item_id,
            "id": item_id,
            "task": req.task,
            "description": req.description or req.task,
            "owner_id": req.owner_id,
            "status": req.status,
            "priority": req.priority,
            "due_date_str": req.due_date_str,
            "meeting_id": req.meeting_id,
            "meeting_title": meeting.title,
            "meeting_date": meeting.meeting_date.isoformat(),
        }

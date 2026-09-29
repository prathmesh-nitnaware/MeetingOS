from typing import Annotated, Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from packages.memory.database import get_db_session
from packages.memory.models import MeetingModel, ProjectModel
from packages.memory.repository import MeetingRepository
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    color: str | None = "#4f46e5"
    status: str = "active"


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str | None = None
    color: str | None = "#4f46e5"
    status: str = "active"
    meeting_count: int = 0
    decision_count: int = 0
    open_action_count: int = 0
    topic_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List all projects for the authenticated organization with aggregated metrics."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.list_projects(org_id=user.org_id)


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Create a new project in the authenticated organization."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.create_project(
            name=req.name,
            description=req.description,
            color=req.color,
            status=req.status,
            org_id=user.org_id,
        )
        await session.commit()
        return {
            "id": proj.id,
            "project_id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "color": proj.color,
            "status": proj.status,
            "meeting_count": 0,
            "decision_count": 0,
            "open_action_count": 0,
            "topic_count": 0,
            "created_at": proj.created_at.isoformat(),
            "updated_at": proj.updated_at.isoformat(),
        }


@router.get("/{project_id}", response_model=dict[str, Any])
async def get_project(
    project_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> dict[str, Any]:
    """Get project details and aggregated overview stats."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        projects = await repo.list_projects(org_id=user.org_id)
        proj = next((p for p in projects if p["id"] == project_id or p["project_id"] == project_id), None)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        return proj


@router.patch("/{project_id}", response_model=dict[str, Any])
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Update project name, description, color, or status."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.update_project(
            project_id=project_id,
            org_id=user.org_id,
            name=req.name,
            description=req.description,
            color=req.color,
            status=req.status,
        )
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        await session.commit()
        return {
            "id": proj.id,
            "project_id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "color": proj.color,
            "status": proj.status,
            "updated_at": proj.updated_at.isoformat(),
        }


@router.delete("/{project_id}", response_model=dict[str, Any])
async def delete_project(
    project_id: str,
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Delete a project and unlink its associated meetings."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        success = await repo.delete_project(project_id=project_id, org_id=user.org_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        await session.commit()
        return {"status": "succeeded", "project_id": project_id, "message": "Project deleted successfully."}


@router.get("/{project_id}/timeline", response_model=list[dict[str, Any]])
async def get_project_timeline(
    project_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """Retrieve chronological timeline of meetings, decisions, and actions for a project."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.get_project(project_id=project_id, org_id=user.org_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        return await repo.get_project_timeline(project_id=project_id, org_id=user.org_id)


@router.get("/{project_id}/meetings", response_model=list[dict[str, Any]])
async def get_project_meetings(
    project_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List all meetings belonging to a project."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.get_project(project_id=project_id, org_id=user.org_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

        stmt = (
            select(MeetingModel)
            .where(
                MeetingModel.project_id == project_id,
                MeetingModel.org_id == user.org_id,
                MeetingModel.deleted_at.is_(None),
            )
            .order_by(MeetingModel.meeting_date.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
        results = []
        for m in rows:
            topics = await repo.get_meeting_topics(m.id)
            decisions = await repo.get_meeting_decisions(m.id)
            actions = await repo.get_meeting_actions(m.id)
            results.append({
                "meeting_id": m.id,
                "id": m.id,
                "title": m.title,
                "meeting_date": m.meeting_date.isoformat(),
                "summary": m.summary,
                "topics": topics,
                "decisions_count": len(decisions),
                "actions_count": len(actions),
                "processing_status": m.processing_status,
                "created_at": m.created_at.isoformat(),
            })
        return results


@router.get("/{project_id}/actions", response_model=list[dict[str, Any]])
async def get_project_actions(
    project_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List action items across all meetings in a project."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.get_project(project_id=project_id, org_id=user.org_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        return await repo.list_all_action_items(org_id=user.org_id, project_id=project_id)


@router.get("/{project_id}/decisions", response_model=list[dict[str, Any]])
async def get_project_decisions(
    project_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """List decisions across all meetings in a project."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        proj = await repo.get_project(project_id=project_id, org_id=user.org_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        return await repo.list_all_decisions(org_id=user.org_id, project_id=project_id)

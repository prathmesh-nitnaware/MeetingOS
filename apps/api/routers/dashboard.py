from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.memory.database import get_db_session
from packages.memory.graph import DashboardMetrics, GraphService
from packages.memory.repository import MeetingRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardMetrics)
async def get_organizational_dashboard(
    user: UserIdentity = Depends(require_viewer),
) -> DashboardMetrics:
    """Retrieve top-level aggregate metrics across the authenticated organisation's meeting memory."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session, org_id=user.org_id)
        return await service.get_dashboard_metrics()


@router.get("/activity", response_model=list[dict[str, Any]])
async def get_activity_feed(
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """Retrieve the 'What Changed?' activity stream across the organization."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.get_activity_feed(org_id=user.org_id, limit=20)

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.memory.database import get_db_session
from packages.memory.graph import DashboardMetrics, GraphService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardMetrics)
async def get_organizational_dashboard(
    user: UserIdentity = Depends(require_viewer),
) -> DashboardMetrics:
    """Retrieve top-level aggregate metrics across the authenticated organisation's meeting memory."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session, org_id=user.org_id)
        return await service.get_dashboard_metrics()

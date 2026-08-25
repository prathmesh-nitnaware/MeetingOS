from apps.api.config import settings
from fastapi import APIRouter
from packages.memory.database import get_db_session
from packages.memory.graph import DashboardMetrics, GraphService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardMetrics)
async def get_organizational_dashboard() -> DashboardMetrics:
    """Retrieve top-level aggregate metrics across organizational meeting memory."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session)
        return await service.get_dashboard_metrics()

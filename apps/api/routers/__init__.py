from apps.api.routers.health import router as health_router
from apps.api.routers.jobs import router as jobs_router
from apps.api.routers.meetings import router as meetings_router

__all__ = ["health_router", "meetings_router", "jobs_router"]

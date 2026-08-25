import sys
from typing import Any

from apps.api.config import settings
from fastapi import APIRouter
from packages.common.models import utc_now
from packages.memory.database import check_database_connection
from packages.memory.redis import check_redis_connection
from pydantic import BaseModel, Field

router = APIRouter(tags=["Health"])


class DependencyHealth(BaseModel):
    database: bool = Field(description="PostgreSQL connectivity status")
    redis: bool = Field(description="Redis connectivity status")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall application status")
    app_name: str
    version: str
    environment: str
    python_version: str
    timestamp: str
    dependencies: DependencyHealth
    details: dict[str, Any] = Field(default_factory=dict)


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Check health of the MeetingOS application and underlying services."""
    db_ok = await check_database_connection(settings.database_url)
    redis_ok = await check_redis_connection(settings.redis_url)

    # In development / mock mode, overall status is 'healthy' while reporting component states
    is_fully_healthy = db_ok and redis_ok
    status_label = "healthy" if is_fully_healthy else "degraded"

    return HealthResponse(
        status=status_label,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        timestamp=utc_now().isoformat(),
        dependencies=DependencyHealth(
            database=db_ok,
            redis=redis_ok,
        ),
        details={
            "debug_mode": settings.app_debug,
            "asr_provider": settings.asr_provider,
            "ner_provider": settings.ner_provider,
            "reasoner_provider": settings.reasoner_provider,
        },
    )

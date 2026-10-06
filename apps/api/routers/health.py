from typing import Any

from apps.api.config import settings
from fastapi import APIRouter, HTTPException, status
from packages.common.models import utc_now
from packages.memory.database import check_database_connection
from packages.memory.redis import check_redis_connection
from pydantic import BaseModel, Field

router = APIRouter(tags=["Health"])


class DependencyHealth(BaseModel):
    database: bool = Field(description="PostgreSQL connectivity status")
    redis: bool = Field(description="Redis connectivity status")


class HealthResponse(BaseModel):
    """Public health summary. Deliberately excludes tenant data and internal configuration."""

    status: str = Field(default="healthy", description="Overall application status")
    app_name: str
    version: str
    environment: str
    timestamp: str
    dependencies: DependencyHealth


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Check health of the MeetingOS application and underlying services."""
    db_ok = await check_database_connection(settings.database_url)
    redis_ok = await check_redis_connection(settings.redis_url)

    return HealthResponse(
        status="healthy" if db_ok and redis_ok else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=utc_now().isoformat(),
        dependencies=DependencyHealth(database=db_ok, redis=redis_ok),
    )


@router.get("/health/ready")
async def get_readiness() -> dict[str, Any]:
    """Readiness probe checking database and redis connection availability."""
    db_ok = await check_database_connection(settings.database_url)
    redis_ok = await check_redis_connection(settings.redis_url)

    if not (db_ok and redis_ok):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": db_ok, "redis": redis_ok},
        )
    return {"status": "ready", "database": True, "redis": True}


@router.get("/health/live")
async def get_liveness() -> dict[str, str]:
    """Liveness probe verifying that the API process is running."""
    return {"status": "alive"}

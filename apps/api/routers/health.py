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

    active_jobs = 0
    failed_jobs = 0
    succeeded_jobs = 0

    if db_ok:
        try:
            from packages.memory.database import get_db_session
            from packages.memory.models import JobModel
            from sqlalchemy import func, select

            async with get_db_session(settings.database_url) as session:
                stmt = select(JobModel.status, func.count(JobModel.id)).group_by(JobModel.status)
                res = await session.execute(stmt)
                counts: dict[str, int] = dict(res.all())  # type: ignore
                active_jobs = counts.get("running", 0) + counts.get("queued", 0)
                failed_jobs = counts.get("failed", 0)
                succeeded_jobs = counts.get("succeeded", 0)
        except Exception:
            pass

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
            "metrics": {
                "active_ingestion_jobs": active_jobs,
                "failed_ingestion_jobs": failed_jobs,
                "succeeded_ingestion_jobs": succeeded_jobs,
            },
        },
    )


@router.get("/health/ready")
async def get_readiness() -> dict[str, Any]:
    """Readiness probe checking database and redis connection availability."""
    from fastapi import HTTPException, status

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

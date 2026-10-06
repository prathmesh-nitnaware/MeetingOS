import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from apps.api.config import settings
from apps.api.middleware.logging import StructuredLoggingMiddleware
from apps.api.routers.admin import router as admin_router
from apps.api.routers.audit import router as audit_router
from apps.api.routers.auth import router as auth_router
from apps.api.routers.connectors import router as connectors_router
from apps.api.routers.dashboard import router as dashboard_router
from apps.api.routers.entities import router as entities_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.health import router as health_router
from apps.api.routers.jobs import router as jobs_router
from apps.api.routers.meetings import router as meetings_router
from apps.api.routers.metrics import router as metrics_router
from apps.api.routers.organizations import router as organizations_router
from apps.api.routers.query import router as query_router
from apps.api.routers.search import router as search_router
from apps.api.routers.temporal import router as temporal_router
from apps.api.routers.traces import router as traces_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from packages.memory.database import get_db_session, get_engine, get_schema_revision
from packages.memory.repository import init_db

logging.basicConfig(level=logging.INFO)
# httpx logs full request URLs at INFO; keep provider credentials out of the logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("meetingos.api")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _expected_schema_revision() -> str | None:
    """Head revision of the Alembic migration scripts shipped with this build."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
        return ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        return None


async def _prepare_database() -> bool:
    """Make sure the schema exists. Returns True when the database is ready to use."""
    if settings.database_url.startswith("sqlite"):
        # SQLite is only used for local experiments and tests: create tables directly.
        await init_db(get_engine(settings.database_url))
        return True

    current = await get_schema_revision(settings.database_url)
    expected = _expected_schema_revision()
    if current is None:
        logger.error(
            "Database has no schema yet. Run `uv run alembic upgrade head` before using the API."
        )
        return False
    if expected and current != expected:
        logger.error(
            "Database schema is at revision %s but this build expects %s. "
            "Run `uv run alembic upgrade head`.",
            current,
            expected,
        )
        return False
    return True


async def _seed_dev_fixtures() -> None:
    from apps.api.dev_fixtures import ensure_dev_fixtures

    async with get_db_session(settings.database_url) as session:
        await ensure_dev_fixtures(session)


async def _retention_loop() -> None:
    """Periodically apply organisations' saved retention policies (auto-delete)."""
    from packages.memory.retention import enforce_retention_policies

    await asyncio.sleep(60)
    while True:
        try:
            async with get_db_session(settings.database_url) as session:
                summary = await enforce_retention_policies(session, settings.upload_storage_dir)
            if summary:
                logger.info("Retention policies enforced: %s", summary)
        except Exception as exc:
            logger.warning("Retention enforcement failed: %s", exc)
        await asyncio.sleep(settings.retention_interval_hours * 3600)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    logger.info(
        "Starting %s v%s in %s mode", settings.app_name, settings.app_version, settings.app_env
    )
    retention_task: asyncio.Task[None] | None = None
    try:
        if await _prepare_database():
            if settings.dev_auth_enabled:
                await _seed_dev_fixtures()
            retention_task = asyncio.create_task(_retention_loop())
    except Exception as exc:
        logger.warning("Database preparation skipped or deferred: %s", exc)

    yield

    if retention_task is not None:
        retention_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await retention_task
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="NLP- and deep-learning-powered organizational memory and decision intelligence system",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        lifespan=lifespan,
    )

    # Middleware registration
    app.add_middleware(StructuredLoggingMiddleware)

    # CORS configuration (credentials are only allowed together with an explicit origin list)
    cors_origins = list(settings.allowed_origins) if settings.allowed_origins else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials="*" not in cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred. Please try again."},
        )

    # Register Routers under /api/v1
    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(organizations_router, prefix=settings.api_v1_prefix)
    app.include_router(meetings_router, prefix=settings.api_v1_prefix)
    app.include_router(jobs_router, prefix=settings.api_v1_prefix)
    app.include_router(search_router, prefix=settings.api_v1_prefix)
    app.include_router(graph_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    app.include_router(entities_router, prefix=settings.api_v1_prefix)
    app.include_router(temporal_router, prefix=settings.api_v1_prefix)
    app.include_router(query_router, prefix=settings.api_v1_prefix)
    app.include_router(connectors_router, prefix=settings.api_v1_prefix)
    app.include_router(audit_router, prefix=settings.api_v1_prefix)
    app.include_router(admin_router, prefix=settings.api_v1_prefix)
    app.include_router(traces_router, prefix=settings.api_v1_prefix)
    app.include_router(metrics_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root_redirect() -> dict[str, str]:
        return {
            "message": "Welcome to MeetingOS API",
            "docs": f"{settings.api_v1_prefix}/docs",
            "health": f"{settings.api_v1_prefix}/health",
            "meetings": f"{settings.api_v1_prefix}/meetings",
        }

    return app


app = create_app()

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apps.api.config import settings
from apps.api.middleware.logging import StructuredLoggingMiddleware
from apps.api.routers.admin import router as admin_router
from apps.api.routers.audit import router as audit_router
from apps.api.routers.connectors import router as connectors_router
from apps.api.routers.dashboard import router as dashboard_router
from apps.api.routers.entities import router as entities_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.health import router as health_router
from apps.api.routers.jobs import router as jobs_router
from apps.api.routers.meetings import router as meetings_router
from apps.api.routers.metrics import router as metrics_router
from apps.api.routers.query import router as query_router
from apps.api.routers.search import router as search_router
from apps.api.routers.temporal import router as temporal_router
from apps.api.routers.traces import router as traces_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.memory.database import get_engine
from packages.memory.repository import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    logger.info(
        "Starting %s v%s in %s mode", settings.app_name, settings.app_version, settings.app_env
    )
    try:
        engine = get_engine(settings.database_url)
        await init_db(engine)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning("Database schema auto-initialization skipped or deferred: %s", exc)

    yield
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

    # CORS configuration
    cors_origins = settings.allowed_origins if settings.allowed_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers under /api/v1
    app.include_router(health_router, prefix=settings.api_v1_prefix)
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

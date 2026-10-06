import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_engine_url: str | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine(database_url: str) -> AsyncEngine:
    """Get or create the process-wide async SQLAlchemy engine for ``database_url``.

    The cache key is the exact URL string the engine was created from. (Comparing against
    ``str(engine.url)`` never matched for password-protected URLs because SQLAlchemy masks
    the password as ``***``, which rebuilt the engine and its pool on every request.)
    """
    global _engine, _engine_url, _session_maker
    if _engine is not None and _engine_url != database_url:
        _engine = None
        _session_maker = None

    if _engine is None:
        engine_kwargs: dict[str, Any] = {
            "echo": False,
            "pool_pre_ping": True,
        }
        if "sqlite" not in database_url:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10

        _engine = create_async_engine(database_url, **engine_kwargs)
        _engine_url = database_url
        _session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


async def dispose_engine() -> None:
    """Close the cached engine's pool. Needed when each unit of work runs in its own event loop
    (Celery tasks call asyncio.run per task; pooled connections cannot cross event loops)."""
    global _engine, _engine_url, _session_maker
    engine = _engine
    _engine = None
    _engine_url = None
    _session_maker = None
    if engine is not None:
        await engine.dispose()


def get_session_maker(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Get session maker for creating async database sessions."""
    get_engine(database_url)
    assert _session_maker is not None
    return _session_maker


@asynccontextmanager
async def get_db_session(database_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for transactional database sessions."""
    session_factory = get_session_maker(database_url)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_schema_revision(database_url: str) -> str | None:
    """Return the Alembic revision recorded in the database, or None if migrations never ran."""
    try:
        engine = get_engine(database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            return result.scalar()
    except Exception:
        return None


async def check_database_connection(database_url: str) -> bool:
    """Perform a lightweight health check ping against PostgreSQL."""
    try:
        engine = get_engine(database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False

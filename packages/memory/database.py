import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine(database_url: str) -> AsyncEngine:
    """Get or create singleton async SQLAlchemy engine."""
    global _engine, _session_maker
    if _engine is None:
        _engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


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

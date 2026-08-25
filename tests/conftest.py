import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from apps.api.config import settings
from apps.api.main import create_app
from httpx import ASGITransport, AsyncClient
from packages.common.enums import SourceType
from packages.common.models import Meeting, Participant, SpeakerInfo, TranscriptSegment
from packages.memory.models import Base
from packages.memory.repository import MeetingRepository, init_db
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
def sample_meeting_data() -> dict:
    fixture_path = (
        Path(__file__).parent.parent / "datasets" / "normalized" / "sample_meeting_001.json"
    )
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_meeting_instance(sample_meeting_data: dict) -> Meeting:
    return Meeting.model_validate(sample_meeting_data)


@pytest.fixture
def minimal_meeting() -> Meeting:
    return Meeting(
        meeting_id="meet-test-01",
        title="Quick Test Standup",
        meeting_date=datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC),
        source_type=SourceType.AUDIO_WAV,
        participants=[Participant(id="p1", canonical_name="Alice")],
        speakers=[SpeakerInfo(speaker_id="spk_0", name="Alice")],
        segments=[
            TranscriptSegment(
                segment_id="seg-1",
                sequence=0,
                speaker_id="spk_0",
                start_time=0.0,
                end_time=5.0,
                text="Hello world.",
            )
        ],
    )


@pytest.fixture
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide an in-memory SQLite async engine with tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    await init_db(engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session with rolled back transactions."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_repository(test_db_session: AsyncSession) -> MeetingRepository:
    return MeetingRepository(test_db_session)


@pytest.fixture
async def async_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with isolated SQLite database and temp storage."""
    test_db_file = tmp_path / "test_meetingos.db"
    test_db_url = f"sqlite+aiosqlite:///{test_db_file.as_posix()}"
    test_storage_dir = tmp_path / "uploads"
    test_storage_dir.mkdir(parents=True, exist_ok=True)

    # Override settings for tests
    settings.database_url = test_db_url
    settings.upload_storage_dir = str(test_storage_dir)

    engine = create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_app = create_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await engine.dispose()

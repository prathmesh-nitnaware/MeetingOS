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

TEST_SETTINGS = {
    "app_env": "test",
    "enable_dev_auth": True,
    # Deterministic offline providers (no model downloads, no network)
    "asr_provider": "mock",
    "diarizer_provider": "mock",
    "embedding_provider": "mock",
    "reasoner_provider": "mock",
    # Never touch the developer's Redis / Celery or rate-limit the test client
    "use_celery": False,
    "rate_limiting_enabled": False,
    # Connector credentials from the developer's .env must not leak into tests
    "teams_enabled": False,
    "teams_tenant_id": None,
    "teams_client_id": None,
    "teams_client_secret": None,
    "zoom_enabled": False,
    "zoom_account_id": None,
    "zoom_client_id": None,
    "zoom_client_secret": None,
    "google_meet_enabled": False,
    "google_client_id": None,
    "google_client_secret": None,
}


@pytest.fixture(autouse=True)
def hermetic_settings():
    """Pin settings to test values for every test and restore them afterwards."""
    saved = {
        name: getattr(settings, name)
        for name in [*TEST_SETTINGS, "database_url", "upload_storage_dir"]
    }
    for name, value in TEST_SETTINGS.items():
        setattr(settings, name, value)
    yield
    for name, value in saved.items():
        setattr(settings, name, value)


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
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer admin-secret-token"}


@pytest.fixture
def member_headers() -> dict[str, str]:
    return {"Authorization": "Bearer member-secret-token"}


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    return {"Authorization": "Bearer viewer-secret-token"}


@pytest.fixture
def beta_auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer admin-beta-token"}


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

    # Back the dev tokens with real organisation/user rows (as the API does at startup)
    from apps.api.dev_fixtures import ensure_dev_fixtures

    async with async_sessionmaker(bind=engine, expire_on_commit=False)() as session:
        await ensure_dev_fixtures(session)
        await session.commit()

    test_app = create_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": "Bearer admin-secret-token"},
    ) as client:
        yield client

    await engine.dispose()

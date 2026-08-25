from datetime import UTC, datetime, timedelta

import pytest
from apps.api.rate_limiter import RateLimiter
from httpx import AsyncClient
from packages.common.enums import SourceType
from packages.common.models import Meeting, Participant, SpeakerInfo, TranscriptSegment
from packages.connectors import (
    ConnectorConfig,
    ConnectorMeeting,
    ConnectorParticipant,
    ConnectorTranscriptSegment,
    DuplicateProviderError,
    GoogleMeetMeetingConnector,
    TeamsMeetingConnector,
    UnknownProviderError,
    ZoomMeetingConnector,
    connector_registry,
)
from packages.memory.models import (
    DecisionModel,
    JobModel,
    MeetingModel,
    TranscriptSegmentModel,
)
from packages.memory.repository import MeetingRepository
from packages.memory.retention import RetentionService
from packages.reasoning.qa import QueryPlan, QueryResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.sync import run_connector_ingestion


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure registry state is clean and registered before each test."""
    connector_registry.clear()
    connector_registry.register(TeamsMeetingConnector())
    connector_registry.register(ZoomMeetingConnector())
    connector_registry.register(GoogleMeetMeetingConnector())
    yield
    connector_registry.clear()


# ==============================================================================
# 1. Connector Registry Tests
# ==============================================================================


def test_connector_registry_operations():
    assert "teams" in connector_registry.list_available()
    assert "zoom" in connector_registry.list_available()
    assert "google_meet" in connector_registry.list_available()

    # Try duplicate registration
    with pytest.raises(DuplicateProviderError):
        connector_registry.register(TeamsMeetingConnector())

    # Get unknown provider
    with pytest.raises(UnknownProviderError):
        connector_registry.get("unknown_provider")


# ==============================================================================
# 2. Individual Connector Configuration, Authentication, & Normalization Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_teams_connector():
    conn = connector_registry.get("teams")
    assert conn.get_provider_name() == "teams"

    # Validate config
    cfg_invalid = ConnectorConfig(provider="teams")
    assert not conn.validate_config(cfg_invalid)

    cfg_valid = ConnectorConfig(
        provider="teams",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
    )
    assert conn.validate_config(cfg_valid)

    # Auth failures
    with pytest.raises(ValueError, match="Missing tenant_id"):
        await conn.authenticate(cfg_invalid)

    cfg_bad_auth = ConnectorConfig(
        provider="teams",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="invalid-secret",
    )
    with pytest.raises(ValueError, match="Invalid Microsoft Graph"):
        await conn.authenticate(cfg_bad_auth)

    # Normalization
    ext_meeting = ConnectorMeeting(
        external_id="ext-teams-01",
        title="Sync Test Teams",
        meeting_date=datetime.now(UTC),
        duration_seconds=300.0,
        participants=[ConnectorParticipant(id="user-01", name="Alice", email="alice@test.com")],
        segments=[
            ConnectorTranscriptSegment(
                speaker_id="user-01", start_time=0.0, end_time=2.0, text="Hi team"
            )
        ],
    )
    cmf = conn.normalize_to_cmf(ext_meeting)
    assert isinstance(cmf, Meeting)
    assert cmf.meeting_id == "meet-teams-ext-teams-01"
    assert cmf.source_provider == "teams"
    assert cmf.external_meeting_id == "ext-teams-01"
    assert len(cmf.segments) == 1
    assert cmf.segments[0].text == "Hi team"


@pytest.mark.asyncio
async def test_zoom_connector():
    conn = connector_registry.get("zoom")
    assert conn.get_provider_name() == "zoom"

    cfg_valid = ConnectorConfig(
        provider="zoom",
        account_id="acc-123",
        client_id="client-123",
        client_secret="secret-123",
    )
    assert conn.validate_config(cfg_valid)

    ext_meeting = ConnectorMeeting(
        external_id="ext-zoom-01",
        title="Sync Test Zoom",
        meeting_date=datetime.now(UTC),
        duration_seconds=300.0,
        participants=[],
        segments=[],
    )
    cmf = conn.normalize_to_cmf(ext_meeting)
    assert cmf.source_provider == "zoom"
    assert cmf.external_meeting_id == "ext-zoom-01"


@pytest.mark.asyncio
async def test_google_meet_connector():
    conn = connector_registry.get("google_meet")
    assert conn.get_provider_name() == "google_meet"

    cfg_valid = ConnectorConfig(
        provider="google_meet",
        client_id="client-123",
        client_secret="secret-123",
    )
    assert conn.validate_config(cfg_valid)

    ext_meeting = ConnectorMeeting(
        external_id="ext-gmeet-01",
        title="Sync Test GMeet",
        meeting_date=datetime.now(UTC),
        duration_seconds=300.0,
        participants=[],
        segments=[],
    )
    cmf = conn.normalize_to_cmf(ext_meeting)
    assert cmf.source_provider == "google_meet"
    assert cmf.external_meeting_id == "ext-gmeet-01"


# ==============================================================================
# 3. Connector Sync & Idempotency Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_ingestion_idempotency():
    # Construct a sample normalized connector meeting
    cmf_meeting = Meeting(
        meeting_id="meet-teams-1111",
        title="Idempotent Standup",
        meeting_date=datetime.now(UTC),
        duration_seconds=120.0,
        source_type=SourceType.SYNTHETIC,
        source_provider="teams",
        external_meeting_id="teams-ext-1111",
        participants=[Participant(id="p-alice", canonical_name="Alice")],
        speakers=[SpeakerInfo(speaker_id="p-alice", name="Alice")],
        segments=[
            TranscriptSegment(
                segment_id="seg-teams-1111-0",
                sequence=0,
                speaker_id="p-alice",
                start_time=0.0,
                end_time=5.0,
                text="Alice: Doing testing for idempotency.",
            )
        ],
    )

    import tempfile
    from pathlib import Path

    from packages.memory.models import Base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    tmp_file = Path(tempfile.gettempdir()) / "test_idempotency.db"
    if tmp_file.exists():
        try:
            tmp_file.unlink()
        except Exception:
            pass

    db_url = f"sqlite+aiosqlite:///{tmp_file.as_posix()}"

    # Initialize tables
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Use an isolated session on the same temp db
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # First Ingestion
    job_id_1 = "job-id-001"
    async with session_maker() as session:
        session.add(
            JobModel(
                id=job_id_1,
                status="queued",
            )
        )
        await session.commit()

    res_1 = await run_connector_ingestion(cmf_meeting, job_id_1, db_url)
    assert res_1["status"] == "succeeded"

    # Verify database has records
    async with session_maker() as session:
        stmt = select(MeetingModel).where(MeetingModel.id == cmf_meeting.meeting_id)
        res_db = await session.execute(stmt)
        meeting_row = res_db.scalar_one_or_none()
        assert meeting_row is not None
        assert meeting_row.source_provider == "teams"
        assert meeting_row.external_meeting_id == "teams-ext-1111"

        # Verify segments inserted
        stmt_seg = select(TranscriptSegmentModel).where(
            TranscriptSegmentModel.meeting_id == cmf_meeting.meeting_id
        )
        res_seg = await session.execute(stmt_seg)
        assert len(res_seg.scalars().all()) == 1

    # Second identical Ingestion
    job_id_2 = "job-id-002"
    async with session_maker() as session:
        session.add(
            JobModel(
                id=job_id_2,
                status="queued",
            )
        )
        await session.commit()

    res_2 = await run_connector_ingestion(cmf_meeting, job_id_2, db_url)
    assert res_2["status"] == "skipped"
    assert res_2["reason"] == "duplicate"

    # Clean up temp db
    await engine.dispose()
    if tmp_file.exists():
        try:
            tmp_file.unlink()
        except Exception:
            pass


# ==============================================================================
# 4. Security, Token Roles, and Redaction Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_api_security_boundary(async_client: AsyncClient):
    # 1. Unauthenticated request rejected
    res = await async_client.get("/api/v1/connectors")
    assert res.status_code == 401

    # 2. Invalid token rejected
    res = await async_client.get(
        "/api/v1/connectors", headers={"Authorization": "Bearer bad-token"}
    )
    assert res.status_code == 401

    # 3. Viewer token can view connectors but cannot sync
    headers_viewer = {"Authorization": "Bearer viewer-secret-token"}
    res = await async_client.get("/api/v1/connectors", headers=headers_viewer)
    assert res.status_code == 200
    connectors_list = res.json()
    assert len(connectors_list) > 0
    # Verify secrets redacted
    for c in connectors_list:
        assert "client_secret" not in c
        assert "access_token" not in c

    res_sync = await async_client.post("/api/v1/connectors/teams/sync", headers=headers_viewer)
    assert res_sync.status_code == 403

    # 4. Admin token can view and has privilege to call sync (will return 400 because config is unconfigured)
    headers_admin = {"Authorization": "Bearer admin-secret-token"}
    res_sync_admin = await async_client.post("/api/v1/connectors/teams/sync", headers=headers_admin)
    # Returns 400 Bad Request because credentials aren't set in config (unconfigured)
    assert res_sync_admin.status_code == 400
    assert "Sync aborted: Configuration is invalid" in res_sync_admin.json()["detail"]


# ==============================================================================
# 5. Rate Limiting Tests
# ==============================================================================


def test_rate_limiter_in_memory_fallback():
    limiter = RateLimiter(limit=2, window_seconds=2)
    key = "test_limit_client_1"

    # First request
    assert limiter.is_allowed(key)
    # Second request
    assert limiter.is_allowed(key)
    # Third request (exceeds limit 2)
    assert not limiter.is_allowed(key)


# ==============================================================================
# 6. Audit & Retention Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_logs(test_db_session: AsyncSession):
    repo = MeetingRepository(test_db_session)
    await repo.create_audit_log(
        actor_id="admin-dev",
        action="ingest_meeting",
        resource_type="meeting",
        resource_id="meet-123",
        outcome="succeeded",
        metadata_json={"file_size": 1024},
    )
    await test_db_session.commit()

    # Retrieve logs
    logs = await repo.get_audit_logs()
    assert len(logs) == 1
    assert logs[0].actor_id == "admin-dev"
    assert logs[0].action == "ingest_meeting"
    assert logs[0].outcome == "succeeded"
    assert logs[0].metadata_json == {"file_size": 1024}


@pytest.mark.asyncio
async def test_retention_purge(test_db_session: AsyncSession):
    # Seed old meeting and new meeting
    old_date = datetime.now(UTC) - timedelta(days=40)
    new_date = datetime.now(UTC)

    old_meet = MeetingModel(
        id="meet-old",
        title="Old Sync",
        meeting_date=old_date,
        source_type="audio/wav",
        created_at=old_date,
    )
    new_meet = MeetingModel(
        id="meet-new",
        title="New Sync",
        meeting_date=new_date,
        source_type="audio/wav",
        created_at=new_date,
    )
    test_db_session.add_all([old_meet, new_meet])
    await test_db_session.commit()

    retention_svc = RetentionService(test_db_session)

    # Dry-run check (meetings older than 30 days)
    dry_results = await retention_svc.run_cleanup(meeting_days=30, dry_run=True)
    assert dry_results["meetings_deleted"] == 1

    # Verify old meeting is still there in dry-run
    stmt = select(MeetingModel).where(MeetingModel.id == "meet-old")
    res_old = await test_db_session.execute(stmt)
    assert res_old.scalar_one_or_none() is not None

    # Real run check
    real_results = await retention_svc.run_cleanup(
        meeting_days=30, dry_run=False, actor_id="admin-dev"
    )
    assert real_results["meetings_deleted"] == 1

    # Verify old meeting is deleted
    res_old_real = await test_db_session.execute(stmt)
    assert res_old_real.scalar_one_or_none() is None

    # Verify new meeting is preserved
    stmt_new = select(MeetingModel).where(MeetingModel.id == "meet-new")
    res_new = await test_db_session.execute(stmt_new)
    assert res_new.scalar_one_or_none() is not None


# ==============================================================================
# 7. Model Versioning Tests
# ==============================================================================


def test_query_response_version_metadata():
    q_resp = QueryResponse(
        question="What database was chosen?",
        answer="PostgreSQL",
        query_plan=QueryPlan(),
        confidence=1.0,
        reasoning_path=[],
    )
    assert q_resp.model_name == "mock-reasoner"
    assert q_resp.model_version == "1.0.0"
    assert q_resp.pipeline_version == "1.0.0"


@pytest.mark.asyncio
async def test_database_version_columns(test_db_session: AsyncSession):
    # Verify default values of model version columns when persisted
    dec = DecisionModel(
        id="dec-123",
        meeting_id="meet-new",
        subject="PostgreSQL choice",
        status="Approved",
    )
    test_db_session.add(dec)
    await test_db_session.commit()

    # Reload from database
    stmt = select(DecisionModel).where(DecisionModel.id == "dec-123")
    res = await test_db_session.execute(stmt)
    dec_row = res.scalar_one()
    assert dec_row.model_name == "mock-nlp-model"
    assert dec_row.model_version == "1.0.0"
    assert dec_row.pipeline_version == "1.0.0"

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from apps.api.main import app
from fastapi.testclient import TestClient
from packages.common.enums import SourceType
from packages.common.models import Meeting
from packages.connectors.calendar import (
    CalendarEvent,
    CalendarRegistry,
    GoogleCalendarProvider,
    MicrosoftCalendarProvider,
)
from packages.memory.models import Base
from packages.memory.repository import MeetingRepository, init_db
from packages.nlp.text_analyzer import normalize_topic_name, sanitize_source_span
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient as StarletteTestClient


def test_topic_normalization():
    """Verify deterministic topic normalization handles case, spacing, and symbols."""
    assert normalize_topic_name("Beta Launch") == "Beta Launch"
    assert normalize_topic_name("  BETA LAUNCH  ") == "Beta Launch"
    assert normalize_topic_name("Beta launch") == "Beta Launch"
    assert normalize_topic_name("Architecture / Infra") == "Architecture / Infra"
    assert normalize_topic_name("") == ""


def test_evidence_bounds_validation_and_sanitization():
    """Verify out-of-bounds, negative, or misaligned source evidence is sanitized."""
    raw_content = "We decided to migrate the primary database to PostgreSQL on Friday."
    content_len = len(raw_content)

    # Valid span
    text, start, end = sanitize_source_span("We decided", 0, 10, raw_content)
    assert start == 0 and end == 10
    assert text == "We decided"

    # Negative bounds: recovered via text match
    text, start, end = sanitize_source_span("We decided", -5, 10, raw_content)
    assert start == 0 and end == 10

    # Exceeding length bounds: recovered via text match
    text, start, end = sanitize_source_span("PostgreSQL", 10, 500, raw_content)
    assert start is not None and end is not None
    assert end <= content_len

    # Text not in raw content with invalid bounds -> returns None, None safely
    text, start, end = sanitize_source_span("Completely made up text", 100, 200, raw_content)
    assert start is None and end is None


@pytest.mark.asyncio
async def test_calendar_provider_abstraction_and_import():
    """Verify CalendarRegistry, providers, and zero-hallucination meeting conversion."""
    registry = CalendarRegistry()
    google_p = GoogleCalendarProvider()
    ms_p = MicrosoftCalendarProvider()

    providers = registry.list_providers()
    assert len(providers) >= 2
    assert "google_calendar" in providers
    assert "microsoft_calendar" in providers

    from packages.connectors.models import ConnectorConfig
    cfg = ConnectorConfig(provider="google_calendar", enabled=True, client_id="test_client", client_secret="test_secret")
    events = await google_p.list_upcoming_events(cfg, limit=5)
    assert len(events) >= 1
    ev = events[0]
    assert isinstance(ev, CalendarEvent)

    # Convert event to meeting draft
    meeting = google_p.convert_event_to_meeting(ev, org_id="test_org")
    assert meeting.title == ev.title
    assert meeting.source_type == SourceType.TEXT_TRANSCRIPT
    assert meeting.metadata.source_filename.startswith("calendar_google_calendar_")
    # Zero notes fabrication: transcript / notes content should be blank for user input
    assert meeting.content == "" or meeting.content is None


@pytest.mark.asyncio
async def test_project_deletion_unlinks_meetings_safely(tmp_path: Path):
    """Verify deleting a project safely unlinks meetings without deleting meeting data."""
    db_file = tmp_path / "test_proj_unlink.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        repo = MeetingRepository(session)
        # Create project
        proj = await repo.create_project(name="Project Deletion Test", org_id="org_test")
        await session.commit()

        # Create meeting assigned to project
        meeting_id = str(uuid.uuid4())
        meeting = Meeting(
            meeting_id=meeting_id,
            title="Meeting in Project",
            meeting_date=datetime.now(UTC),
            project_id=proj.id,
            content="Discussing project tasks.",
        )
        await repo.create_meeting(meeting, org_id="org_test")
        await session.commit()

        # Check meeting has project_id
        fetched = await repo.get_meeting(meeting_id, org_id="org_test")
        assert fetched is not None
        assert fetched.project_id == proj.id

        # Delete project
        deleted = await repo.delete_project(proj.id, org_id="org_test")
        assert deleted is True
        await session.commit()

        # Meeting should still exist, but project_id unlinked
        meeting_after = await repo.get_meeting(meeting_id, org_id="org_test")
        assert meeting_after is not None
        assert meeting_after.project_id is None


@pytest.mark.asyncio
async def test_calendar_api_endpoints(tmp_path: Path):
    """Verify Calendar API endpoints via AsyncClient with isolated database."""
    from apps.api.config import settings
    from apps.api.main import create_app
    from httpx import ASGITransport, AsyncClient

    db_file = tmp_path / "test_calendar_api.db"
    settings.database_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(settings.database_url)
    await init_db(engine)

    app_instance = create_app()
    transport = ASGITransport(app=app_instance)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = {"Authorization": "Bearer member-secret-token"}

        # 1. Get providers
        resp = await client.get("/api/v1/calendar/providers", headers=headers)
        assert resp.status_code == 200
        providers = resp.json()
        assert len(providers) >= 2

        # 2. Get events
        resp = await client.get("/api/v1/calendar/events?provider=google_calendar", headers=headers)
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert "external_event_id" in events[0]
        assert "title" in events[0]

        # 3. Import event
        import_payload = {
            "provider": "google_calendar",
            "external_event_id": events[0]["external_event_id"],
            "title": events[0]["title"],
        }
        resp = await client.post("/api/v1/calendar/import", json=import_payload, headers=headers)
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "imported"
        assert "meeting_id" in res


def test_collaboration_websocket_endpoint():
    """Verify real-time presence and review broadcast over WebSocket."""
    client = StarletteTestClient(app)
    meeting_id = "test_collab_meeting"

    with client.websocket_connect(f"/ws/meetings/{meeting_id}?user_name=Alice&user_id=usr_alice") as ws1:
        # Initial presence frame
        data = ws1.receive_json()
        assert data["type"] == "initial_presence"
        assert any(v["user_name"] == "Alice" for v in data["active_viewers"])

        # Second client connects
        with client.websocket_connect(f"/ws/meetings/{meeting_id}?user_name=Bob&user_id=usr_bob") as ws2:
            data2 = ws2.receive_json()
            assert data2["type"] == "initial_presence"
            assert len(data2["active_viewers"]) == 2

            # Alice sends a review update
            ws1.send_json({
                "type": "review_action",
                "entity_type": "decision",
                "entity_id": "dec_123",
                "review_status": "confirmed",
            })

            # Bob receives the review sync broadcast
            sync_msg = ws2.receive_json()
            assert sync_msg["type"] == "review_sync"
            assert sync_msg["entity_type"] == "decision"
            assert sync_msg["entity_id"] == "dec_123"
            assert sync_msg["review_status"] == "confirmed"
            assert sync_msg["actor_name"] == "Alice"

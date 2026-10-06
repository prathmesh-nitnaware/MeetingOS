"""PostgreSQL-specific behaviour the SQLite test database cannot catch.

Opt-in: set MEETINGOS_TEST_POSTGRES_URL to an EMPTY, disposable database, e.g.
    MEETINGOS_TEST_POSTGRES_URL=postgresql+asyncpg://meetingos:meetingos_secret_password@localhost:5432/meetingos_test
All tables in that database are dropped at the end of the test.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from apps.api.config import settings
from apps.api.main import create_app
from httpx import ASGITransport, AsyncClient
from packages.memory.database import dispose_engine
from packages.memory.models import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

PG_URL = os.getenv("MEETINGOS_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="MEETINGOS_TEST_POSTGRES_URL not set")

DEV = {"Authorization": "Bearer admin-secret-token"}


@pytest.fixture
async def pg_client(tmp_path) -> AsyncGenerator[AsyncClient, None]:
    assert PG_URL
    engine = create_async_engine(PG_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from apps.api.dev_fixtures import ensure_dev_fixtures

    async with async_sessionmaker(bind=engine, expire_on_commit=False)() as session:
        await ensure_dev_fixtures(session)
        await session.commit()

    settings.database_url = PG_URL
    settings.upload_storage_dir = str(tmp_path / "uploads")
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://t"
    ) as client:
        yield client

    await dispose_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_temporal_endpoints_work_on_postgres(pg_client: AsyncClient):
    for title, date, body in (
        (
            "Week 1",
            "2026-09-01",
            b"Priya: We decided to adopt PostgreSQL for the storage layer.\nRahul: I will finish the schema migration by Friday.\nPriya: The login timeout problem is blocking the release.\n",
        ),
        (
            "Week 2",
            "2026-09-08",
            b"Priya: We decided to switch from PostgreSQL to MySQL for the storage layer instead.\nPriya: The login timeout problem is still blocking the release.\n",
        ),
    ):
        res = await pg_client.post(
            "/api/v1/meetings",
            headers=DEV,
            data={"title": title, "meeting_date": date},
            files={"file": ("n.txt", body, "text/plain")},
        )
        assert res.status_code == 201, res.text

    meetings = (await pg_client.get("/api/v1/meetings", headers=DEV)).json()
    week1 = next(m for m in meetings if m["title"] == "Week 1")["meeting_id"]
    decision = (await pg_client.get(f"/api/v1/meetings/{week1}/decisions", headers=DEV)).json()[0]
    action = (await pg_client.get(f"/api/v1/meetings/{week1}/actions", headers=DEV)).json()[0]
    issue = (await pg_client.get(f"/api/v1/meetings/{week1}/issues", headers=DEV)).json()[0]

    # These used ILIKE on a JSON column and returned 500 on PostgreSQL
    for path in (
        f"/api/v1/decisions/{decision['decision_id']}/history",
        f"/api/v1/commitments/{action['commitment_id']}/history",
        f"/api/v1/issues/{issue['issue_id']}/history",
    ):
        res = await pg_client.get(path, headers=DEV)
        assert res.status_code == 200, (path, res.text)

    history = (
        await pg_client.get(f"/api/v1/decisions/{decision['decision_id']}/history", headers=DEV)
    ).json()
    assert history["status"] == "Reversed"
    assert any(e["event_type"] == "DECISION_REVERSED" for e in history["events"])

    entity_id = (await pg_client.get("/api/v1/entities", headers=DEV)).json()[0]["id"]
    assert (
        await pg_client.get(f"/api/v1/entities/{entity_id}/timeline", headers=DEV)
    ).status_code == 200
    assert (
        await pg_client.get("/api/v1/timeline", params={"entity_id": entity_id}, headers=DEV)
    ).status_code == 200

    agentic = (
        await pg_client.post(
            "/api/v1/query/agentic",
            headers=DEV,
            json={"question": "What happened to the PostgreSQL decision?"},
        )
    ).json()
    assert all(step["status"] != "failed" for step in agentic["trace"]), agentic["trace"]

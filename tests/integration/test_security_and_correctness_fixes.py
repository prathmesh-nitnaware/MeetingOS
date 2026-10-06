"""Regression tests for the security, tenancy and correctness fixes (issue audit, 2026-09)."""

import inspect
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from apps.api.config import Settings, settings
from httpx import AsyncClient
from packages.memory.database import get_engine
from sqlalchemy import text

DEV = {"Authorization": "Bearer admin-secret-token"}
MEMBER = {"Authorization": "Bearer member-secret-token"}
BETA = {"Authorization": "Bearer admin-beta-token"}


async def _upload(
    client: AsyncClient,
    headers: dict,
    title: str,
    body: bytes,
    name: str = "notes.txt",
    ctype: str = "text/plain",
) -> dict:
    res = await client.post(
        "/api/v1/meetings",
        headers=headers,
        data={"title": title, "meeting_date": "2026-09-01"},
        files={"file": (name, body, ctype)},
    )
    assert res.status_code == 201, res.text
    return res.json()


# --------------------------------------------------------------------------- authentication


@pytest.mark.asyncio
async def test_login_requires_the_correct_password(async_client: AsyncClient):
    reg = await async_client.post(
        "/api/v1/auth/register-org",
        json={
            "org_name": "Victim Corp",
            "org_slug": "victim-corp",
            "admin_name": "Victim Owner",
            "admin_email": "owner@victim.example",
            "admin_password": "Correct-Horse-1",
        },
    )
    assert reg.status_code == 200

    no_pw = await async_client.post("/api/v1/auth/login", json={"email": "owner@victim.example"})
    wrong = await async_client.post(
        "/api/v1/auth/login", json={"email": "owner@victim.example", "password": "nope-nope"}
    )
    right = await async_client.post(
        "/api/v1/auth/login", json={"email": "owner@victim.example", "password": "Correct-Horse-1"}
    )
    assert no_pw.status_code == 401
    assert wrong.status_code == 401
    assert right.status_code == 200


@pytest.mark.asyncio
async def test_admin_email_backdoor_is_gone(async_client: AsyncClient):
    res = await async_client.post(
        "/api/v1/auth/login", json={"email": "badminton-fan@evil.example"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_register_org_cannot_take_over_an_existing_account(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register-org",
        json={
            "org_name": "Victim Corp",
            "org_slug": "victim-two",
            "admin_name": "Victim",
            "admin_email": "victim2@victim.example",
            "admin_password": "Victim-Password-1",
        },
    )
    attack = await async_client.post(
        "/api/v1/auth/register-org",
        json={
            "org_name": "Attacker Org",
            "org_slug": "attacker-org",
            "admin_name": "x",
            "admin_email": "victim2@victim.example",
        },
    )
    assert attack.status_code == 409


def test_production_rejects_placeholder_secret_key():
    with pytest.raises(ValueError, match="MEETINGOS_SECRET_KEY"):
        Settings(
            app_env="production",
            app_debug=False,
            database_url="postgresql+asyncpg://u:StrongPw123@db:5432/x",
            MEETINGOS_SECRET_KEY="change-this-to-a-secure-random-secret-key-in-production",
            MEETINGOS_ALLOWED_ORIGINS="https://app.example.com",
        )


@pytest.mark.asyncio
async def test_invitation_roles_cannot_exceed_the_inviter(async_client: AsyncClient):
    owner_attempt = await async_client.post(
        "/api/v1/organizations/current/invitations",
        headers=DEV,
        json={"email": "friend@example.com", "role": "owner"},
    )
    assert owner_attempt.status_code == 403
    bogus_role = await async_client.post(
        "/api/v1/organizations/current/invitations",
        headers=DEV,
        json={"email": "friend@example.com", "role": "superuser"},
    )
    assert bogus_role.status_code == 422
    ok = await async_client.post(
        "/api/v1/organizations/current/invitations",
        headers=DEV,
        json={"email": "friend@example.com", "role": "member"},
    )
    assert ok.status_code == 200


# ----------------------------------------------------------------------------- tenancy


@pytest.mark.asyncio
async def test_other_tenants_cannot_rewrite_or_read_lifecycle_data(async_client: AsyncClient):
    dev_m = await _upload(
        async_client,
        DEV,
        "Dev architecture sync",
        b"Priya: We decided to adopt PostgreSQL for the storage layer.\n",
    )
    decisions = (
        await async_client.get(f"/api/v1/meetings/{dev_m['meeting_id']}/decisions", headers=DEV)
    ).json()
    dec_id = decisions[0]["decision_id"]
    before = decisions[0]["status"]

    await _upload(
        async_client,
        BETA,
        "Beta infra review",
        b"Sam: We decided to switch from PostgreSQL to MySQL for the storage layer instead.\n",
    )
    after = (
        await async_client.get(f"/api/v1/meetings/{dev_m['meeting_id']}/decisions", headers=DEV)
    ).json()[0]["status"]
    assert after == before

    history = await async_client.get(f"/api/v1/decisions/{dec_id}/history", headers=BETA)
    assert history.status_code == 404
    reconcile = await async_client.post(
        "/api/v1/temporal/reconcile", headers=BETA, json={"meeting_id": dev_m["meeting_id"]}
    )
    assert reconcile.status_code == 404


@pytest.mark.asyncio
async def test_retention_cleanup_only_touches_the_callers_org(async_client: AsyncClient):
    dev_m = await _upload(async_client, DEV, "Old dev meeting", b"Priya: Status update.\n")
    engine = get_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE meetings SET created_at = :d WHERE id = :m"),
            {"d": datetime.now(UTC) - timedelta(days=60), "m": dev_m["meeting_id"]},
        )
    res = await async_client.post(
        "/api/v1/admin/retention/cleanup",
        params={"meeting_days": 7, "dry_run": "false"},
        headers=BETA,
    )
    assert res.status_code == 200
    assert res.json()["deleted"]["meetings_deleted"] == 0
    still_there = await async_client.get(f"/api/v1/meetings/{dev_m['meeting_id']}", headers=DEV)
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_jobs_require_login_and_are_tenant_scoped(async_client: AsyncClient):
    m = await _upload(async_client, DEV, "Job scoping", b"Priya: Hello.\n")
    assert (
        await async_client.get(f"/api/v1/jobs/{m['job_id']}", headers={"Authorization": ""})
    ).status_code == 401
    assert (await async_client.get(f"/api/v1/jobs/{m['job_id']}", headers=BETA)).status_code == 404
    assert (await async_client.get(f"/api/v1/jobs/{m['job_id']}", headers=DEV)).status_code == 200


@pytest.mark.asyncio
async def test_members_cannot_delete_meetings(async_client: AsyncClient):
    m = await _upload(async_client, DEV, "Board meeting", b"Priya: Numbers look fine.\n")
    denied = await async_client.delete(
        f"/api/v1/meetings/{m['meeting_id']}", params={"hard_delete": "true"}, headers=MEMBER
    )
    assert denied.status_code == 403
    allowed = await async_client.delete(f"/api/v1/meetings/{m['meeting_id']}", headers=DEV)
    assert allowed.status_code == 200


# ---------------------------------------------------------------------------- correctness


@pytest.mark.asyncio
async def test_soft_deleted_meetings_disappear_from_search_and_answers(async_client: AsyncClient):
    m = await _upload(
        async_client, DEV, "Confidential", b"Priya: We decided to cut the zebra budget.\n"
    )
    await async_client.delete(f"/api/v1/meetings/{m['meeting_id']}", headers=DEV)

    search = (await async_client.get("/api/v1/search", params={"q": "zebra"}, headers=DEV)).json()
    answer = (
        await async_client.post(
            "/api/v1/query", headers=DEV, json={"question": "What happened to the zebra budget?"}
        )
    ).json()
    dashboard = (await async_client.get("/api/v1/dashboard", headers=DEV)).json()
    assert search["total_results"] == 0
    assert answer["evidence"] == []
    assert dashboard["meetings_ingested"] == 0


@pytest.mark.parametrize("reasoner", ["mock", "local"])
@pytest.mark.asyncio
async def test_answers_are_grounded_in_the_evidence(async_client: AsyncClient, reasoner: str):
    settings.reasoner_provider = reasoner
    await _upload(
        async_client, DEV, "DB choice", b"Ana: We decided to use Oracle as our database.\n"
    )
    ans = (
        await async_client.post(
            "/api/v1/query", headers=DEV, json={"question": "Which database did we decide on?"}
        )
    ).json()
    assert "Oracle" in ans["answer"]
    assert "PostgreSQL" not in ans["answer"]


@pytest.mark.asyncio
async def test_audio_download_keeps_its_real_type(async_client: AsyncClient):
    m = await _upload(async_client, DEV, "Voice memo", os.urandom(2048), "memo.mp3", "audio/mpeg")
    res = await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/audio", headers=DEV)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/mpeg")
    assert "memo.mp3" in res.headers["content-disposition"]


@pytest.mark.asyncio
async def test_reextraction_and_reconciliation_are_idempotent(async_client: AsyncClient):
    first = await _upload(
        async_client,
        DEV,
        "Week 1",
        b"Priya: We decided to adopt PostgreSQL for the storage layer.\n",
    )
    second = await async_client.post(
        "/api/v1/meetings",
        headers=DEV,
        data={"title": "Week 2", "meeting_date": "2026-09-08"},
        files={
            "file": (
                "n.txt",
                b"Priya: We decided to switch from PostgreSQL to MySQL for the storage layer instead.\n",
                "text/plain",
            )
        },
    )
    second_id = second.json()["meeting_id"]

    async def timeline_types() -> list[str]:
        res = await async_client.get(f"/api/v1/meetings/{second_id}/timeline", headers=DEV)
        return sorted(e["event_type"] for e in res.json())

    base = await timeline_types()
    assert "DECISION_REVERSED" in base

    for _ in range(2):
        await async_client.post(
            "/api/v1/temporal/reconcile", headers=DEV, json={"meeting_id": second_id}
        )
    assert await timeline_types() == base

    await async_client.post(f"/api/v1/meetings/{second_id}/extract", headers=DEV)
    await async_client.post(f"/api/v1/meetings/{first['meeting_id']}/extract", headers=DEV)
    assert await timeline_types() == base
    first_status = (
        await async_client.get(f"/api/v1/meetings/{first['meeting_id']}/decisions", headers=DEV)
    ).json()[0]["status"]
    assert first_status == "Reversed"


@pytest.mark.asyncio
async def test_history_endpoints_and_entity_timeline_work(async_client: AsyncClient):
    m = await _upload(
        async_client,
        DEV,
        "History",
        b"Rahul: I will finish the schema migration by Friday.\nPriya: We decided to adopt PostgreSQL.\n",
    )
    decision = (
        await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/decisions", headers=DEV)
    ).json()[0]
    action = (
        await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/actions", headers=DEV)
    ).json()[0]
    assert (
        await async_client.get(f"/api/v1/decisions/{decision['decision_id']}/history", headers=DEV)
    ).status_code == 200
    assert (
        await async_client.get(
            f"/api/v1/commitments/{action['commitment_id']}/history", headers=DEV
        )
    ).status_code == 200
    entities = (await async_client.get("/api/v1/entities", headers=DEV)).json()
    assert entities and "entity_type" in entities[0]
    timeline = await async_client.get(f"/api/v1/entities/{entities[0]['id']}/timeline", headers=DEV)
    assert timeline.status_code == 200
    filtered = await async_client.get(
        "/api/v1/timeline", params={"entity_id": entities[0]["id"]}, headers=DEV
    )
    assert filtered.status_code == 200


@pytest.mark.asyncio
async def test_timeline_events_link_to_their_facts(async_client: AsyncClient):
    m = await _upload(async_client, DEV, "Links", b"Priya: We decided to adopt PostgreSQL.\n")
    events = (
        await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/timeline", headers=DEV)
    ).json()
    decision_events = [e for e in events if e["event_type"] == "DECISION_APPROVED"]
    assert decision_events and decision_events[0]["payload"]["decision_id"].startswith("dec-")
    transcript = (
        await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/transcript", headers=DEV)
    ).json()
    segment_ids = {s["segment_id"] for s in transcript["segments"]}
    decision = (
        await async_client.get(f"/api/v1/meetings/{m['meeting_id']}/decisions", headers=DEV)
    ).json()[0]
    assert decision["evidence_segment_id"] in segment_ids


def test_engine_is_reused_for_password_protected_urls():
    url = "postgresql+asyncpg://user:secret-password@localhost:5432/db"
    assert get_engine(url) is get_engine(url)


def test_celery_tasks_do_not_carry_credentials():
    from workers.tasks.ingestion import process_meeting_task
    from workers.tasks.sync import sync_connector_task

    for task in (process_meeting_task, sync_connector_task):
        celery_task: Any = task  # Celery task object; its .run is the wrapped function
        params = inspect.signature(celery_task.run).parameters
        assert "database_url" not in params
        assert "config_dict" not in params

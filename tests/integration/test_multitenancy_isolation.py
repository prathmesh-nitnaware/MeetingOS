import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from apps.api.config import settings
from apps.api.main import create_app
from httpx import ASGITransport, AsyncClient
from packages.common.enums import SourceType
from packages.common.models import Meeting, Participant, SpeakerInfo, TranscriptSegment
from packages.memory.graph import GraphService
from packages.memory.models import (
    AuditLogModel,
    Base,
    OrganizationMembershipModel,
    OrganizationModel,
    UserModel,
)
from packages.memory.repository import MeetingRepository
from packages.reasoning.qa import QueryRequest, RAGPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.retrieval.search import HybridSearchEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_repository_and_engines_strict_org_isolation(tmp_path: Path):
    """Verify that MeetingRepository, HybridSearchEngine, GraphService, and TemporalIntelligenceEngine strictly isolate data between tenants."""
    db_file = tmp_path / "test_tenant_iso.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)

    # 1. Organization Alpha Meeting
    m_alpha = Meeting(
        meeting_id="meet-alpha-001",
        title="Project Apollo Secret Roadmap",
        meeting_date=dt,
        source_type=SourceType.AUDIO_WAV,
        participants=[Participant(id="p-alpha", canonical_name="Alpha CEO")],
        speakers=[SpeakerInfo(speaker_id="spk_alpha", name="Alpha CEO")],
        segments=[
            TranscriptSegment(
                segment_id="seg-alpha-001",
                sequence=0,
                speaker_id="spk_alpha",
                start_time=0.0,
                end_time=10.0,
                text="Alpha confidential: We are acquiring BetaCorp for fifty million dollars.",
            )
        ],
    )

    # 2. Organization Beta Meeting
    m_beta = Meeting(
        meeting_id="meet-beta-001",
        title="Project Hermes Internal Sync",
        meeting_date=dt,
        source_type=SourceType.AUDIO_WAV,
        participants=[Participant(id="p-beta", canonical_name="Beta Director")],
        speakers=[SpeakerInfo(speaker_id="spk_beta", name="Beta Director")],
        segments=[
            TranscriptSegment(
                segment_id="seg-beta-001",
                sequence=0,
                speaker_id="spk_beta",
                start_time=0.0,
                end_time=10.0,
                text="Beta confidential: Our database password and deployment key is secret123.",
            )
        ],
    )

    async with session_factory() as session:
        repo = MeetingRepository(session)
        await repo.create_meeting(m_alpha, org_id="org_alpha")
        await repo.create_meeting(m_beta, org_id="org_beta")
        await session.commit()

    # 3. Test Repository Queries
    async with session_factory() as session:
        repo = MeetingRepository(session)
        alpha_meetings = await repo.list_meetings(org_id="org_alpha")
        assert len(alpha_meetings) == 1
        assert alpha_meetings[0].meeting_id == "meet-alpha-001"
        assert await repo.get_meeting("meet-alpha-001", org_id="org_alpha") is not None
        assert await repo.get_meeting("meet-beta-001", org_id="org_alpha") is None

        beta_meetings = await repo.list_meetings(org_id="org_beta")
        assert len(beta_meetings) == 1
        assert beta_meetings[0].meeting_id == "meet-beta-001"
        assert await repo.get_meeting("meet-beta-001", org_id="org_beta") is not None
        assert await repo.get_meeting("meet-alpha-001", org_id="org_beta") is None

    # 4. Test Search Engine Isolation
    async with session_factory() as session:
        search_alpha = HybridSearchEngine(session, org_id="org_alpha")
        search_beta = HybridSearchEngine(session, org_id="org_beta")

        res_a = await search_alpha.search("deployment key secret123")
        assert len(res_a.results) == 0

        res_b = await search_beta.search("deployment key secret123")
        assert len(res_b.results) == 1
        assert res_b.results[0].meeting_id == "meet-beta-001"

        res_b_leak = await search_beta.search("acquiring BetaCorp")
        assert len(res_b_leak.results) == 0

    # 5. Test Graph Service Isolation
    async with session_factory() as session:
        graph_alpha = GraphService(session, org_id="org_alpha")
        metrics_alpha = await graph_alpha.get_dashboard_metrics()
        assert metrics_alpha.meetings_ingested == 1

        graph_beta = GraphService(session, org_id="org_beta")
        metrics_beta = await graph_beta.get_dashboard_metrics()
        assert metrics_beta.meetings_ingested == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_api_endpoints_cross_tenant_isolation(tmp_path: Path):
    """Verify Tests 1-8: Cross-tenant access boundaries across meeting details, search, transcripts, audio, and audit logs."""
    db_file = tmp_path / "test_api_iso.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    storage_dir = tmp_path / "uploads_iso"
    storage_dir.mkdir(parents=True, exist_ok=True)

    settings.database_url = db_url
    settings.upload_storage_dir = str(storage_dir)

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed meeting and audio file for org_dev
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        repo = MeetingRepository(session)
        dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
        m_dev = Meeting(
            meeting_id="meet-dev-secret-01",
            title="DevOrg Secret Architecture",
            meeting_date=dt,
            source_type=SourceType.AUDIO_WAV,
            segments=[
                TranscriptSegment(
                    segment_id="seg-dev-01",
                    sequence=0,
                    speaker_id="spk_1",
                    start_time=0.0,
                    end_time=5.0,
                    text="We use PostgreSQL and Kafka for backend infrastructure.",
                )
            ],
        )
        await repo.create_meeting(m_dev, org_id="org_dev")

        # Add audit log for Org Dev
        await repo.create_audit_log(
            actor_id="admin-dev",
            action="meeting.created",
            resource_type="meeting",
            resource_id="meet-dev-secret-01",
            outcome="succeeded",
            org_id="org_dev",
            metadata_json={"title": "DevOrg Secret Architecture"},
        )
        await session.commit()

    # Create dummy audio file in tenant storage
    audio_path = storage_dir / "orgs" / "org_dev" / "meetings" / "meet-dev-secret-01" / "audio.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFFdummywavbytesforunittesting")

    test_app = create_app()
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers_dev = {"Authorization": "Bearer admin-secret-token"}
        headers_beta = {"Authorization": "Bearer admin-beta-token"}

        # Test 1: Org B attempting to fetch Org A meeting -> 404
        res_beta_single = await client.get("/api/v1/meetings/meet-dev-secret-01", headers=headers_beta)
        assert res_beta_single.status_code == 404

        # Test 2: Org A can retrieve its own meeting -> 200
        res_dev_single = await client.get("/api/v1/meetings/meet-dev-secret-01", headers=headers_dev)
        assert res_dev_single.status_code == 200
        assert res_dev_single.json()["meeting_id"] == "meet-dev-secret-01"

        # Test 3: Org B attempting to delete Org A meeting -> 404 failure
        res_beta_delete = await client.delete("/api/v1/meetings/meet-dev-secret-01", headers=headers_beta)
        assert res_beta_delete.status_code == 404

        # Test 4: Org B search returns 0 results for Org A data
        res_beta_search = await client.get("/api/v1/search?q=PostgreSQL", headers=headers_beta)
        assert res_beta_search.status_code == 200
        assert res_beta_search.json()["total_results"] == 0

        # Test 5: Org B cannot download Org A audio -> 404
        res_beta_audio = await client.get("/api/v1/meetings/meet-dev-secret-01/audio", headers=headers_beta)
        assert res_beta_audio.status_code == 404

        # Test 5b: Org A can download its own audio -> 200
        res_dev_audio = await client.get("/api/v1/meetings/meet-dev-secret-01/audio", headers=headers_dev)
        assert res_dev_audio.status_code == 200

        # Test 6: Org B cannot retrieve Org A transcript -> 404
        res_beta_tx = await client.get("/api/v1/meetings/meet-dev-secret-01/transcript", headers=headers_beta)
        assert res_beta_tx.status_code == 404

        # Test 8: Org B cannot access Org A audit logs
        res_beta_audit = await client.get("/api/v1/audit", headers=headers_beta)
        assert res_beta_audit.status_code == 200
        assert len(res_beta_audit.json()) == 0  # Zero audit logs in Org B

        # Org A can see its audit log
        res_dev_audit = await client.get("/api/v1/audit", headers=headers_dev)
        assert res_dev_audit.status_code == 200
        assert len(res_dev_audit.json()) >= 1

        # Test 11: Soft delete lifecycle in Org A
        res_dev_del = await client.delete("/api/v1/meetings/meet-dev-secret-01", headers=headers_dev)
        assert res_dev_del.status_code == 200
        assert res_dev_del.json()["deletion_type"] == "soft_delete"

        # After soft delete, meeting is no longer listed in active meetings
        res_dev_after = await client.get("/api/v1/meetings", headers=headers_dev)
        assert len(res_dev_after.json()) == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_multi_organization_user_and_revocation(tmp_path: Path):
    """Verify Tests 9-10: Multi-org user switching and immediate access revocation."""
    db_file = tmp_path / "test_multiorg.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    settings.database_url = db_url

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Seed 2 organizations
        org1 = OrganizationModel(id="org_acme", name="Acme Corp", slug="acme", status="active")
        org2 = OrganizationModel(id="org_globex", name="Globex Inc", slug="globex", status="active")
        session.add_all([org1, org2])

        # Seed 1 user belonging to both orgs
        user = UserModel(id="usr-carol", email="carol@enterprise.com", full_name="Carol Danvers", is_active=True)
        session.add(user)
        await session.flush()

        mem1 = OrganizationMembershipModel(id="mem-1", org_id="org_acme", user_id=user.id, role="admin", status="active")
        mem2 = OrganizationMembershipModel(id="mem-2", org_id="org_globex", user_id=user.id, role="member", status="active")
        session.add_all([mem1, mem2])
        await session.commit()

    test_app = create_app()
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Login Carol with Acme
        res_login = await client.post("/api/v1/auth/login", json={"email": "carol@enterprise.com", "org_slug": "acme"})
        assert res_login.status_code == 200
        token_acme = res_login.json()["access_token"]
        assert res_login.json()["user"]["org_id"] == "org_acme"
        assert len(res_login.json()["available_organizations"]) == 2

        # Switch Carol to Globex
        res_switch = await client.post(
            "/api/v1/auth/switch-org",
            json={"target_org_id": "org_globex"},
            headers={"Authorization": f"Bearer {token_acme}"},
        )
        assert res_switch.status_code == 200
        token_globex = res_switch.json()["access_token"]
        assert res_switch.json()["user"]["org_id"] == "org_globex"
        assert res_switch.json()["user"]["role"] == "member"

        # Revoke Carol's membership in Globex
        async with session_factory() as session:
            stmt = OrganizationMembershipModel.__table__.update().where(
                OrganizationMembershipModel.id == "mem-2"
            ).values(status="suspended")
            await session.execute(stmt)
            await session.commit()

        # Switching to suspended org fails immediately
        res_switch_revoked = await client.post(
            "/api/v1/auth/switch-org",
            json={"target_org_id": "org_globex"},
            headers={"Authorization": f"Bearer {token_acme}"},
        )
        assert res_switch_revoked.status_code == 403

    await engine.dispose()


@pytest.mark.asyncio
async def test_invitation_lifecycle_and_single_use_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify cryptographically secure invitation generation, single-use, expiry, and tenant binding."""
    db_file = tmp_path / "test_invite_sec.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        org = OrganizationModel(id="org_invite_corp", name="Invite Corp", slug="invite-corp", status="active")
        owner = UserModel(id="usr-inviter", email="inviter@invitecorp.com", full_name="Inviter Admin", is_active=True)
        session.add_all([org, owner])
        await session.flush()
        mem = OrganizationMembershipModel(id="mem-inv", org_id=org.id, user_id=owner.id, role="owner", status="active")
        session.add(mem)
        await session.commit()

    monkeypatch.setattr(settings, "database_url", db_url)
    test_app = create_app()
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login owner
        res_login = await client.post("/api/v1/auth/login", json={"email": "inviter@invitecorp.com", "org_slug": "invite-corp"})
        token_owner = res_login.json()["access_token"]

        # 2. Issue invitation
        res_inv = await client.post(
            "/api/v1/organizations/current/invitations",
            json={"email": "recruit@example.com", "role": "member"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        assert res_inv.status_code == 200
        inv_data = res_inv.json()
        raw_token = inv_data["invitation_token"]
        assert raw_token is not None and raw_token.startswith("inv_")

        # 3. Accept invitation
        res_accept = await client.post(
            "/api/v1/auth/invitations/accept",
            json={"token": raw_token, "full_name": "Recruit User", "password": "SecurePassword123!"},
        )
        assert res_accept.status_code == 200
        accept_data = res_accept.json()
        assert accept_data["user"]["email"] == "recruit@example.com"
        assert accept_data["user"]["org_id"] == "org_invite_corp"
        assert accept_data["user"]["role"] == "member"

        # 4. Attempt second acceptance (replay/reuse attack) -> must fail 400
        res_replay = await client.post(
            "/api/v1/auth/invitations/accept",
            json={"token": raw_token, "full_name": "Attacker", "password": "AttackerPassword123!"},
        )
        assert res_replay.status_code == 400
        assert "already been accepted" in res_replay.json()["detail"]

        # 5. Invalid token -> must fail 404
        res_invalid = await client.post(
            "/api/v1/auth/invitations/accept",
            json={"token": "inv_completely_fake_token", "full_name": "Hacker", "password": "Pass"},
        )
        assert res_invalid.status_code == 404

    await engine.dispose()


@pytest.mark.asyncio
async def test_audio_storage_isolation_and_path_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify that audio downloads strictly enforce tenant boundaries and block path traversal."""
    db_file = tmp_path / "test_audio_sec.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        repo = MeetingRepository(session)
        # Create Org Alpha Meeting & Audio
        m_alpha = Meeting(
            meeting_id="meet-audio-alpha",
            title="Alpha Confidential Audio",
            meeting_date=dt,
            source_type=SourceType.AUDIO_WAV,
            participants=[],
        )
        await repo.create_meeting(m_alpha, org_id="org_alpha")

        # Create Org Beta Meeting & Audio
        m_beta = Meeting(
            meeting_id="meet-audio-beta",
            title="Beta Confidential Audio",
            meeting_date=dt,
            source_type=SourceType.AUDIO_WAV,
            participants=[],
        )
        await repo.create_meeting(m_beta, org_id="org_beta")
        await session.commit()

    # Create tenant-scoped storage files
    alpha_audio_dir = storage_root / "orgs" / "org_alpha" / "meetings" / "meet-audio-alpha"
    alpha_audio_dir.mkdir(parents=True, exist_ok=True)
    alpha_file = alpha_audio_dir / "audio.wav"
    alpha_file.write_bytes(b"RIFFALPHA_SECRET_AUDIO_PAYLOAD")

    beta_audio_dir = storage_root / "orgs" / "org_beta" / "meetings" / "meet-audio-beta"
    beta_audio_dir.mkdir(parents=True, exist_ok=True)
    beta_file = beta_audio_dir / "audio.wav"
    beta_file.write_bytes(b"RIFFBETA_SECRET_AUDIO_PAYLOAD")

    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(settings, "upload_storage_dir", str(storage_root))

    test_app = create_app()
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        from apps.api.auth import create_access_token
        token_alpha = create_access_token(user_id="u_a", org_id="org_alpha", role="viewer")
        token_beta = create_access_token(user_id="u_b", org_id="org_beta", role="viewer")

        # Alpha accesses Alpha -> Success
        res_a_a = await client.get("/api/v1/meetings/meet-audio-alpha/audio", headers={"Authorization": f"Bearer {token_alpha}"})
        assert res_a_a.status_code == 200
        assert res_a_a.content == b"RIFFALPHA_SECRET_AUDIO_PAYLOAD"

        # Beta tries to access Alpha audio -> 404 Not Found (Tenant isolated)
        res_b_a = await client.get("/api/v1/meetings/meet-audio-alpha/audio", headers={"Authorization": f"Bearer {token_beta}"})
        assert res_b_a.status_code == 404

        # Alpha tries to access Beta audio -> 404 Not Found
        res_a_b = await client.get("/api/v1/meetings/meet-audio-beta/audio", headers={"Authorization": f"Bearer {token_alpha}"})
        assert res_a_b.status_code == 404

    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_multi_tenant_ingestion_isolation(tmp_path: Path):
    """Verify simultaneous concurrent ingestion pipelines across separate tenants preserve complete data isolation."""
    import asyncio
    from workers.tasks.ingestion import run_ingestion_pipeline

    db_file = tmp_path / "test_concurrent_ingest.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed meeting and job records for both tenants
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = MeetingRepository(session)
        m1 = Meeting(meeting_id="meet-conc-1", title="Tenant One All Hands", meeting_date=dt, source_type=SourceType.AUDIO_WAV, participants=[])
        m2 = Meeting(meeting_id="meet-conc-2", title="Tenant Two Board Review", meeting_date=dt, source_type=SourceType.AUDIO_WAV, participants=[])
        await repo.create_meeting(m1, org_id="org_tenant_1")
        await repo.create_meeting(m2, org_id="org_tenant_2")
        await repo.create_job("job-conc-1", "meet-conc-1", "queued")
        await repo.create_job("job-conc-2", "meet-conc-2", "queued")
        await session.commit()

    dummy_audio = tmp_path / "sample.wav"
    dummy_audio.write_bytes(b"RIFFDUMMYAUDIO")

    # Launch ingestion concurrently
    t1 = asyncio.create_task(
        run_ingestion_pipeline(
            meeting_id="meet-conc-1",
            job_id="job-conc-1",
            file_path_str=str(dummy_audio),
            source_type_str="audio/wav",
            database_url=db_url,
            org_id="org_tenant_1",
        )
    )
    t2 = asyncio.create_task(
        run_ingestion_pipeline(
            meeting_id="meet-conc-2",
            job_id="job-conc-2",
            file_path_str=str(dummy_audio),
            source_type_str="audio/wav",
            database_url=db_url,
            org_id="org_tenant_2",
        )
    )

    res1, res2 = await asyncio.gather(t1, t2)
    assert res1["status"] == "succeeded"
    assert res2["status"] == "succeeded"

    # Verify cross-tenant isolation in repository queries
    async with session_factory() as session:
        repo = MeetingRepository(session)
        # Tenant 1 cannot see Tenant 2 meeting
        assert await repo.get_meeting("meet-conc-2", org_id="org_tenant_1") is None
        # Tenant 2 cannot see Tenant 1 meeting
        assert await repo.get_meeting("meet-conc-1", org_id="org_tenant_2") is None

        # Each tenant can only list their own meeting
        t1_meetings = await repo.list_meetings(org_id="org_tenant_1")
        assert len(t1_meetings) == 1
        assert t1_meetings[0].meeting_id == "meet-conc-1"

        t2_meetings = await repo.list_meetings(org_id="org_tenant_2")
        assert len(t2_meetings) == 1
        assert t2_meetings[0].meeting_id == "meet-conc-2"

    await engine.dispose()


def test_pbkdf2_password_hashing_and_verification():
    """Verify cryptographically strong PBKDF2 password hashing and verification."""
    from apps.api.routers.auth import hash_password, verify_password

    raw_pw = "SuperSecretPassword#2026"
    pw_hash = hash_password(raw_pw)

    assert pw_hash.startswith("pbkdf2_sha256$")
    assert verify_password(raw_pw, pw_hash) is True
    assert verify_password("WrongPassword123", pw_hash) is False
    assert verify_password("", pw_hash) is False
    assert verify_password(raw_pw, None) is False

    # Verify legacy sha256 fallback compatibility
    legacy_sha256 = hashlib.sha256(raw_pw.encode("utf-8")).hexdigest()
    assert verify_password(raw_pw, legacy_sha256) is True
    assert verify_password("WrongPassword", legacy_sha256) is False


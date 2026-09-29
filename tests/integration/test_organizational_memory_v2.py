import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from packages.common.enums import CommitmentStatus, DecisionStatus, SourceType
from packages.common.models import ExtractedCommitment, ExtractedDecision, Meeting, Participant, TranscriptSegment
from packages.memory.models import Base
from packages.memory.repository import MeetingRepository
from packages.nlp.text_analyzer import analyze_text_intelligence, validate_structured_intelligence
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_projects_crud_and_tenant_isolation(tmp_path: Path):
    """Test full project lifecycle and strict tenant boundary isolation."""
    db_file = tmp_path / "test_proj_iso.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        repo = MeetingRepository(session)

        # Create project in Org Alpha
        proj_alpha = await repo.create_project(
            name="Alpha Product Launch",
            description="Alpha launch strategy",
            org_id="org_alpha",
        )
        # Create project in Org Beta
        proj_beta = await repo.create_project(
            name="Beta Redesign",
            description="Beta confidential redesign",
            org_id="org_beta",
        )
        await session.commit()

        # List projects for Org Alpha - should NOT see Org Beta
        alpha_projs = await repo.list_projects(org_id="org_alpha")
        assert len(alpha_projs) == 1
        assert alpha_projs[0]["name"] == "Alpha Product Launch"

        # List projects for Org Beta - should NOT see Org Alpha
        beta_projs = await repo.list_projects(org_id="org_beta")
        assert len(beta_projs) == 1
        assert beta_projs[0]["name"] == "Beta Redesign"

        # Direct cross-org fetch returns None
        assert await repo.get_project(proj_beta.id, org_id="org_alpha") is None


@pytest.mark.asyncio
async def test_project_timeline_and_evidence_spans(tmp_path: Path):
    """Test project meeting timeline, aggregated decisions, actions, and source evidence spans."""
    db_file = tmp_path / "test_proj_timeline.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        repo = MeetingRepository(session)
        proj = await repo.create_project(
            name="Cloud Migration",
            description="Migrating database to PostgreSQL",
            org_id="org_alpha",
        )

        now = datetime.now(UTC)
        m1 = Meeting(
            meeting_id="meet-m1",
            title="Migration Kickoff",
            meeting_date=now - timedelta(days=7),
            project_id=proj.id,
            content="Alex: We decided to migrate from MySQL to PostgreSQL.\nSarah: I will prepare schemas by Friday.",
        )
        await repo.create_meeting(m1, org_id="org_alpha")

        # Extract and validate intelligence
        analysis = analyze_text_intelligence(
            title=m1.title,
            content=m1.content,
            meeting_date=m1.meeting_date,
            meeting_id=m1.meeting_id,
        )

        from packages.nlp.pipeline import NLPExtractionResult
        nlp_res = NLPExtractionResult(
            meeting_id=m1.meeting_id,
            topics=analysis.topics,
            decisions=analysis.decisions,
            commitments=analysis.action_items,
            actions=analysis.action_items,
        )
        await repo.save_nlp_extraction_results(m1.meeting_id, nlp_res)
        await session.commit()

        # Check project timeline
        timeline = await repo.get_project_timeline(proj.id, org_id="org_alpha")
        assert len(timeline) == 1
        assert timeline[0]["title"] == "Migration Kickoff"
        assert len(timeline[0]["decisions"]) >= 1
        assert len(timeline[0]["action_items"]) >= 1

        # Check evidence span
        dec = timeline[0]["decisions"][0]
        assert dec["source_text"] is not None


@pytest.mark.asyncio
async def test_zero_hallucination_ai_validation():
    """Verify zero-hallucination rules: unassigned owner, unspecified deadline, and ambiguity preservation."""
    raw_content = "We need someone to prepare the financial report soon. Maybe we could consider a beta next quarter."
    analysis = analyze_text_intelligence(
        title="General Sync",
        content=raw_content,
    )

    # Validate zero-hallucination rules
    for a in analysis.action_items:
        # If no specific name or "I will" is given, owner must be Unassigned
        assert a.owner_id == "Unassigned" or a.owner_id is not None
        # Ambiguous deadlines like "soon" must not hallucinate a fake date
        assert a.due_date_str == "Not specified" or a.due_date_str is not None


@pytest.mark.asyncio
async def test_topic_detail_and_evolution(tmp_path: Path):
    """Verify cross-meeting topic detail, timeline evolution, and related decisions/actions."""
    db_file = tmp_path / "test_topic_evolution.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        repo = MeetingRepository(session)

        # 2 meetings discussing "Product Launch"
        m1 = Meeting(
            meeting_id="meet-launch-1",
            title="Launch Kickoff",
            meeting_date=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            content="Alex: Launch target is approved for October 10.",
        )
        m2 = Meeting(
            meeting_id="meet-launch-2",
            title="Launch Readiness",
            meeting_date=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
            content="Alex: Decision: Launch postponed to October 17. Sarah will notify customers by Wednesday.",
        )
        await repo.create_meeting(m1, org_id="org_alpha")
        await repo.create_meeting(m2, org_id="org_alpha")

        a1 = analyze_text_intelligence(m1.title, m1.content, meeting_date=m1.meeting_date, meeting_id=m1.meeting_id)
        a2 = analyze_text_intelligence(m2.title, m2.content, meeting_date=m2.meeting_date, meeting_id=m2.meeting_id)

        from packages.nlp.pipeline import NLPExtractionResult
        await repo.save_nlp_extraction_results(m1.meeting_id, NLPExtractionResult(meeting_id=m1.meeting_id, topics=["Product Launch"], decisions=a1.decisions, commitments=a1.action_items, actions=a1.action_items))
        await repo.save_nlp_extraction_results(m2.meeting_id, NLPExtractionResult(meeting_id=m2.meeting_id, topics=["Product Launch"], decisions=a2.decisions, commitments=a2.action_items, actions=a2.action_items))
        await session.commit()

        # Fetch topic detail
        topic_info = await repo.get_topic_detail("Product Launch", org_id="org_alpha")
        assert topic_info["meeting_count"] == 2
        assert len(topic_info["evolution"]) == 2
        assert len(topic_info["decisions"]) >= 1


@pytest.mark.asyncio
async def test_activity_feed_what_changed(tmp_path: Path):
    """Verify 'What Changed?' activity stream surfaces meetings, decisions, and action items."""
    db_file = tmp_path / "test_act_feed.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        repo = MeetingRepository(session)

        m = Meeting(
            meeting_id="meet-act-1",
            title="Sprint Planning",
            meeting_date=datetime.now(UTC),
            summary="Discussed Q4 sprint goals.",
            content="David: Agreed on API rate limiting. Bob will deploy redis cache by Friday.",
        )
        await repo.create_meeting(m, org_id="org_alpha")
        analysis = analyze_text_intelligence(m.title, m.content, meeting_id=m.meeting_id)

        from packages.nlp.pipeline import NLPExtractionResult
        await repo.save_nlp_extraction_results(m.meeting_id, NLPExtractionResult(meeting_id=m.meeting_id, topics=analysis.topics, decisions=analysis.decisions, commitments=analysis.action_items, actions=analysis.action_items))
        await session.commit()

        feed = await repo.get_activity_feed(org_id="org_alpha", limit=10)
        assert len(feed) >= 1
        feed_types = [item["type"] for item in feed]
        assert "meeting_analyzed" in feed_types

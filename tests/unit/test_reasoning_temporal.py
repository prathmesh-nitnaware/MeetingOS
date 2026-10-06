from datetime import UTC, datetime

import pytest
from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    EventType,
    IssueStatus,
    SourceType,
)
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedIssue,
    Meeting,
    TranscriptSegment,
)
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionResult
from packages.reasoning.temporal import TemporalIntelligenceEngine


@pytest.mark.asyncio
async def test_decision_reversal_and_modification_lifecycle(test_repository: MeetingRepository):
    engine = TemporalIntelligenceEngine(test_repository.session)
    dt1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC)

    # 1. Meeting 1: Initial decision to use MongoDB
    m1 = Meeting(
        meeting_id="m-dec-01",
        title="Initial DB Selection",
        meeting_date=dt1,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s1",
                sequence=0,
                speaker_id="spk_rahul",
                start_time=0.0,
                end_time=5.0,
                text="We decided to adopt MongoDB database.",
            )
        ],
    )
    await test_repository.create_meeting(m1)
    await test_repository.save_nlp_extraction_results(
        "m-dec-01",
        NLPExtractionResult(
            meeting_id="m-dec-01",
            entities=[
                ExtractedEntity(
                    entity_id="ent-mongo", name="MongoDB", entity_type=EntityType.TECHNOLOGY
                )
            ],
            decisions=[
                ExtractedDecision(
                    decision_id="dec-mongo",
                    subject="Adopt MongoDB for document storage",
                    status=DecisionStatus.APPROVED,
                    meeting_id="m-dec-01",
                )
            ],
        ),
    )

    # 2. Meeting 2: Decision reversal replacing MongoDB with PostgreSQL
    m2 = Meeting(
        meeting_id="m-dec-02",
        title="DB Migration Architecture",
        meeting_date=dt2,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s2",
                sequence=0,
                speaker_id="spk_rahul",
                start_time=0.0,
                end_time=5.0,
                text="We decided to adopt PostgreSQL which replaces MongoDB database.",
            )
        ],
    )
    await test_repository.create_meeting(m2)
    await test_repository.save_nlp_extraction_results(
        "m-dec-02",
        NLPExtractionResult(
            meeting_id="m-dec-02",
            entities=[
                ExtractedEntity(
                    entity_id="ent-postgres", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
                ),
                ExtractedEntity(
                    entity_id="ent-mongo", name="MongoDB", entity_type=EntityType.TECHNOLOGY
                ),
            ],
            decisions=[
                ExtractedDecision(
                    decision_id="dec-pg",
                    subject="Adopt PostgreSQL which replaces MongoDB",
                    status=DecisionStatus.APPROVED,
                    meeting_id="m-dec-02",
                )
            ],
        ),
    )

    # 3. Run temporal reconciliation
    result = await engine.reconcile_meeting_lifecycle("m-dec-02")
    assert result.decision_changes_detected >= 1
    assert result.events_created >= 1

    # 4. Check decision history
    history = await engine.reconstruct_decision_history("dec-mongo")
    assert history is not None
    assert history.decision.status == DecisionStatus.REVERSED
    assert any(e.event_type == EventType.DECISION_REVERSED for e in history.events)


@pytest.mark.asyncio
async def test_commitment_deadline_slippage_lifecycle(test_repository: MeetingRepository):
    engine = TemporalIntelligenceEngine(test_repository.session)
    dt1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    dl1 = datetime(2026, 8, 10, 18, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 8, 8, 10, 0, 0, tzinfo=UTC)
    dl2 = datetime(2026, 8, 20, 18, 0, 0, tzinfo=UTC)

    # Meeting 1: Initial deadline
    m1 = Meeting(
        meeting_id="m-com-01",
        title="Sprint Planning",
        meeting_date=dt1,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s1",
                sequence=0,
                speaker_id="spk_priya",
                start_time=0.0,
                end_time=5.0,
                text="Priya: Finish API integration by Aug 10",
            )
        ],
    )
    await test_repository.create_meeting(m1)
    await test_repository.save_nlp_extraction_results(
        "m-com-01",
        NLPExtractionResult(
            meeting_id="m-com-01",
            commitments=[
                ExtractedCommitment(
                    commitment_id="com-api",
                    description="Finish API integration",
                    owner_id="spk_priya",
                    status=CommitmentStatus.ASSIGNED,
                    original_deadline=dl1,
                    current_deadline=dl1,
                    meeting_id="m-com-01",
                )
            ],
        ),
    )

    # Meeting 2: Deadline extended/slipped to Aug 20
    m2 = Meeting(
        meeting_id="m-com-02",
        title="Sprint Sync",
        meeting_date=dt2,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s2",
                sequence=0,
                speaker_id="spk_priya",
                start_time=0.0,
                end_time=5.0,
                text="Priya: Finish API integration by Aug 20",
            )
        ],
    )
    await test_repository.create_meeting(m2)
    await test_repository.save_nlp_extraction_results(
        "m-com-02",
        NLPExtractionResult(
            meeting_id="m-com-02",
            commitments=[
                ExtractedCommitment(
                    commitment_id="com-api-rev",
                    description="Finish API integration",
                    owner_id="spk_priya",
                    status=CommitmentStatus.IN_PROGRESS,
                    original_deadline=dl2,
                    current_deadline=dl2,
                    meeting_id="m-com-02",
                )
            ],
        ),
    )

    result = await engine.reconcile_meeting_lifecycle("m-com-02")
    assert result.deadline_changes_detected >= 1

    history = await engine.reconstruct_commitment_history("com-api")
    assert history is not None
    assert history.deadline_changes_count >= 1
    assert any(e.event_type == EventType.DEADLINE_CHANGED for e in history.events)


@pytest.mark.asyncio
async def test_recurring_and_resolved_issue_lifecycle(test_repository: MeetingRepository):
    engine = TemporalIntelligenceEngine(test_repository.session)
    dt1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC)
    dt3 = datetime(2026, 8, 10, 10, 0, 0, tzinfo=UTC)

    # Meeting 1: Issue detected
    m1 = Meeting(
        meeting_id="m-iss-01",
        title="Sync 1",
        meeting_date=dt1,
        source_type=SourceType.AUDIO_WAV,
        segments=[],
    )
    await test_repository.create_meeting(m1)
    await test_repository.save_nlp_extraction_results(
        "m-iss-01",
        NLPExtractionResult(
            meeting_id="m-iss-01",
            issues=[
                ExtractedIssue(
                    issue_id="iss-cache",
                    description="Redis cache connection pool timeout",
                    status=IssueStatus.DETECTED,
                    first_detected_at=dt1,
                )
            ],
        ),
    )

    # Meeting 2: Issue recurs
    m2 = Meeting(
        meeting_id="m-iss-02",
        title="Sync 2",
        meeting_date=dt2,
        source_type=SourceType.AUDIO_WAV,
        segments=[],
    )
    await test_repository.create_meeting(m2)
    await test_repository.save_nlp_extraction_results(
        "m-iss-02",
        NLPExtractionResult(
            meeting_id="m-iss-02",
            issues=[
                ExtractedIssue(
                    issue_id="iss-cache-recur",
                    description="Redis cache connection pool timeout",
                    status=IssueStatus.DETECTED,
                    first_detected_at=dt2,
                )
            ],
        ),
    )
    res2 = await engine.reconcile_meeting_lifecycle("m-iss-02")
    assert res2.recurring_issues_detected >= 1

    h2 = await engine.reconstruct_issue_history("iss-cache")
    assert h2 is not None
    assert h2.is_recurring is True

    # Meeting 3: Issue resolved
    m3 = Meeting(
        meeting_id="m-iss-03",
        title="Sync 3",
        meeting_date=dt3,
        source_type=SourceType.AUDIO_WAV,
        segments=[],
    )
    await test_repository.create_meeting(m3)
    await test_repository.save_nlp_extraction_results(
        "m-iss-03",
        NLPExtractionResult(
            meeting_id="m-iss-03",
            issues=[
                ExtractedIssue(
                    issue_id="iss-cache-fix",
                    description="Redis cache connection pool timeout resolved",
                    status=IssueStatus.RESOLVED,
                    first_detected_at=dt3,
                )
            ],
        ),
    )
    await engine.reconcile_meeting_lifecycle("m-iss-03")

    h3 = await engine.reconstruct_issue_history("iss-cache")
    assert h3 is not None
    assert h3.is_resolved is True
    assert any(e.event_type == EventType.ISSUE_RESOLVED for e in h3.events)

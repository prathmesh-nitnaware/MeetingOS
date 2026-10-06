from datetime import UTC, datetime

import pytest
from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    EventType,
    IssueStatus,
    RelationType,
    SourceType,
    UtteranceClass,
)
from packages.common.models import (
    EvidenceItem,
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIssue,
    ExtractedRelation,
    Meeting,
    TranscriptSegment,
)
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionResult, UtteranceClassificationItem


@pytest.mark.asyncio
async def test_repository_save_and_get_nlp_facts(test_repository: MeetingRepository):
    meeting = Meeting(
        meeting_id="meet-nlp-001",
        title="NLP Persistence Test",
        meeting_date=datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC),
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="seg-1",
                sequence=0,
                speaker_id="spk_0",
                start_time=0.0,
                end_time=5.0,
                text="Rahul: We decided on Postgres.",
            )
        ],
    )
    await test_repository.create_meeting(meeting)

    nlp_result = NLPExtractionResult(
        meeting_id="meet-nlp-001",
        entities=[
            ExtractedEntity(entity_id="ent-rahul", name="Rahul", entity_type=EntityType.PERSON),
            ExtractedEntity(
                entity_id="ent-postgres", name="Postgres", entity_type=EntityType.TECHNOLOGY
            ),
        ],
        topics=["Database Migration"],
        decisions=[
            ExtractedDecision(
                decision_id="dec-1",
                subject="Adopt Postgres",
                status=DecisionStatus.APPROVED,
                meeting_id="meet-nlp-001",
            )
        ],
        commitments=[
            ExtractedCommitment(
                commitment_id="com-1",
                description="Finish migration",
                owner_id="spk_0",
                status=CommitmentStatus.IN_PROGRESS,
                meeting_id="meet-nlp-001",
            )
        ],
        issues=[
            ExtractedIssue(
                issue_id="iss-1",
                description="Redis cache timeout",
                owner_id="spk_0",
                status=IssueStatus.DETECTED,
                first_detected_at=datetime.now(UTC),
            )
        ],
        events=[
            ExtractedEvent(
                event_id="evt-1",
                event_type=EventType.DECISION_APPROVED,
                occurred_at=datetime.now(UTC),
                meeting_id="meet-nlp-001",
                subject_entity_id="ent-postgres",
            )
        ],
        relations=[
            ExtractedRelation(
                relation_id="rel-1",
                source_entity_id="ent-rahul",
                target_entity_id="ent-postgres",
                relationship_type=RelationType.ASSIGNED_TO,
                meeting_id="meet-nlp-001",
            )
        ],
        classifications=[
            UtteranceClassificationItem(segment_id="seg-1", classes=[UtteranceClass.DECISION])
        ],
        evidence=[
            EvidenceItem(
                meeting_id="meet-nlp-001",
                segment_id="seg-1",
                start_time=0.0,
                end_time=5.0,
                text_snapshot="Rahul: We decided on Postgres.",
            )
        ],
    )

    await test_repository.save_nlp_extraction_results("meet-nlp-001", nlp_result)

    # Verify query functions
    entities = await test_repository.get_meeting_entities("meet-nlp-001")
    assert len(entities) == 2
    assert {e.name for e in entities} == {"Rahul", "Postgres"}

    topics = await test_repository.get_meeting_topics("meet-nlp-001")
    assert topics == ["Database Migration"]

    decisions = await test_repository.get_meeting_decisions("meet-nlp-001")
    assert len(decisions) == 1
    assert decisions[0].subject == "Adopt Postgres"

    actions = await test_repository.get_meeting_actions("meet-nlp-001")
    assert len(actions) == 1
    assert actions[0].description == "Finish migration"

    issues = await test_repository.get_meeting_issues("meet-nlp-001")
    assert len(issues) == 1
    assert issues[0].description == "Redis cache timeout"

    timeline = await test_repository.get_meeting_timeline("meet-nlp-001")
    assert len(timeline) == 1
    assert timeline[0].event_type == EventType.DECISION_APPROVED

    relations = await test_repository.get_meeting_relations("meet-nlp-001")
    assert len(relations) == 1
    assert relations[0].relationship_type == RelationType.ASSIGNED_TO

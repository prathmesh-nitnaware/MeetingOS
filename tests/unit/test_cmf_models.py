from datetime import UTC, datetime

import pytest
from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    EventType,
    IssueStatus,
    ProcessingStatus,
    RelationType,
    SourceType,
    UtteranceClass,
)
from packages.common.models import (
    AnswerWithAttribution,
    EvidenceItem,
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIssue,
    ExtractedRelation,
    ExtractedUtteranceClassification,
    Meeting,
    NormalizedTemporal,
    Participant,
    TranscriptSegment,
)
from pydantic import ValidationError


def test_valid_meeting_construction(minimal_meeting: Meeting):
    assert minimal_meeting.title == "Quick Test Standup"
    assert minimal_meeting.source_type == SourceType.AUDIO_WAV
    assert minimal_meeting.processing_status == ProcessingStatus.QUEUED
    assert len(minimal_meeting.segments) == 1
    assert minimal_meeting.segments[0].start_time == 0.0
    assert minimal_meeting.segments[0].end_time == 5.0


def test_fixture_loading(sample_meeting_instance: Meeting):
    assert sample_meeting_instance.meeting_id == "meet-2026-08-25-arch-001"
    assert len(sample_meeting_instance.participants) == 3
    assert len(sample_meeting_instance.speakers) == 3
    assert len(sample_meeting_instance.segments) == 8
    assert sample_meeting_instance.segments[0].speaker_id == "spk_0"
    assert sample_meeting_instance.metadata.model_pipeline_version == "1.0.0"


def test_serialization_and_deserialization(sample_meeting_instance: Meeting):
    json_str = sample_meeting_instance.model_dump_json()
    assert isinstance(json_str, str)
    reconstructed = Meeting.model_validate_json(json_str)
    assert reconstructed.meeting_id == sample_meeting_instance.meeting_id
    assert len(reconstructed.segments) == len(sample_meeting_instance.segments)
    assert reconstructed.meeting_date == sample_meeting_instance.meeting_date


def test_invalid_segment_timestamp():
    with pytest.raises(ValidationError) as exc:
        TranscriptSegment(
            segment_id="seg-invalid",
            sequence=0,
            speaker_id="spk_0",
            start_time=10.0,
            end_time=5.0,  # Invalid: end_time < start_time
            text="Invalid timestamp segment",
        )
    assert "end_time" in str(exc.value)


def test_negative_timestamp():
    with pytest.raises(ValidationError):
        TranscriptSegment(
            segment_id="seg-invalid",
            sequence=0,
            speaker_id="spk_0",
            start_time=-1.0,
            end_time=5.0,
            text="Negative start time",
        )


def test_out_of_order_segment_sequence():
    with pytest.raises(ValidationError) as exc:
        Meeting(
            meeting_id="meet-err",
            title="Out of Order Meeting",
            meeting_date=datetime.now(UTC),
            segments=[
                TranscriptSegment(
                    segment_id="s1",
                    sequence=1,
                    speaker_id="spk_0",
                    start_time=0.0,
                    end_time=5.0,
                    text="First",
                ),
                TranscriptSegment(
                    segment_id="s2",
                    sequence=0,  # Invalid: sequence must be strictly increasing
                    speaker_id="spk_0",
                    start_time=5.1,
                    end_time=10.0,
                    text="Second",
                ),
            ],
        )
    assert "Segment sequence out of order" in str(exc.value)


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        Participant.model_validate(
            {
                "id": "p1",
                "canonical_name": "Alice",
                "unexpected_field": "not_allowed",  # Extra fields are forbidden
            }
        )


def test_extracted_facts_and_evidence():
    entity = ExtractedEntity(
        entity_id="e1",
        name="PostgreSQL",
        entity_type=EntityType.TECHNOLOGY,
        start_char=10,
        end_char=20,
        segment_id="seg-001",
    )
    assert entity.confidence == 1.0

    classification = ExtractedUtteranceClassification(
        segment_id="seg-001",
        classes=[UtteranceClass.DECISION, UtteranceClass.ACTION],
    )
    assert len(classification.classes) == 2

    relation = ExtractedRelation(
        source_entity_id="e1",
        target_entity_id="e2",
        relationship_type=RelationType.ASSIGNED_TO,
        meeting_id="m1",
    )
    assert relation.relationship_type == RelationType.ASSIGNED_TO

    event = ExtractedEvent(
        event_type=EventType.DECISION_APPROVED,
        occurred_at=datetime.now(UTC),
        meeting_id="m1",
        subject_entity_id="e1",
    )
    assert event.event_type == EventType.DECISION_APPROVED

    decision = ExtractedDecision(
        subject="Adopt PostgreSQL",
        status=DecisionStatus.APPROVED,
        meeting_id="m1",
    )
    assert decision.status == DecisionStatus.APPROVED

    commitment = ExtractedCommitment(
        description="Finish schema",
        status=CommitmentStatus.ASSIGNED,
        meeting_id="m1",
    )
    assert commitment.status == CommitmentStatus.ASSIGNED

    issue = ExtractedIssue(
        description="Connection timeouts",
        status=IssueStatus.DETECTED,
    )
    assert issue.status == IssueStatus.DETECTED

    evidence = EvidenceItem(
        meeting_id="m1",
        segment_id="s1",
        start_time=10.0,
        end_time=20.0,
        text_snapshot="We will adopt PostgreSQL.",
    )
    answer = AnswerWithAttribution(
        question="What database was chosen?",
        answer="PostgreSQL was chosen.",
        evidence=[evidence],
    )
    assert len(answer.evidence) == 1
    assert answer.evidence[0].start_time == 10.0


def test_temporal_normalization():
    now = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
    temp = NormalizedTemporal(
        text="tomorrow",
        normalized_date=now,
    )
    assert temp.normalized_date == now

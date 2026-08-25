from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

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
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class BaseSchema(BaseModel):
    """Base schema with strict validation and standard configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
        validate_assignment=True,
    )


# ------------------------------------------------------------------------------
# Common Meeting Format (CMF) Core Schemas
# ------------------------------------------------------------------------------


class Participant(BaseSchema):
    """Represents a human participant in a meeting."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_name: str = Field(..., min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)


class SpeakerInfo(BaseSchema):
    """Speaker diarization label mapping to known participant."""

    speaker_id: str = Field(..., min_length=1, max_length=100)
    name: str | None = None
    canonical_entity_id: str | None = None


class TranscriptSegment(BaseSchema):
    """A single continuous utterance by a speaker with timestamps."""

    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence: int = Field(..., ge=0)
    speaker_id: str = Field(..., min_length=1, max_length=100)
    start_time: float = Field(..., ge=0.0, description="Start timestamp in seconds")
    end_time: float = Field(..., ge=0.0, description="End timestamp in seconds")
    text: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "TranscriptSegment":
        if self.end_time < self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) cannot be earlier than start_time ({self.start_time})"
            )
        return self


class MeetingMetadata(BaseSchema):
    """Technical and ingestion metadata for a meeting."""

    source_filename: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    audio_sample_rate_hz: int | None = Field(default=None, gt=0)
    audio_channels: int | None = Field(default=None, gt=0)
    audio_duration_seconds: float | None = Field(default=None, ge=0.0)
    model_pipeline_version: str = "1.0.0"
    extra: dict[str, Any] = Field(default_factory=dict)


class Meeting(BaseSchema):
    """Canonical Meeting entity in the Common Meeting Format (CMF)."""

    meeting_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=500)
    meeting_date: datetime
    duration_seconds: float | None = Field(default=None, ge=0.0)
    source_type: SourceType = SourceType.AUDIO_WAV
    processing_status: ProcessingStatus = ProcessingStatus.QUEUED
    participants: list[Participant] = Field(default_factory=list)
    speakers: list[SpeakerInfo] = Field(default_factory=list)
    segments: list[TranscriptSegment] = Field(default_factory=list)
    metadata: MeetingMetadata = Field(default_factory=MeetingMetadata)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("meeting_date", "created_at", "updated_at", mode="after")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    @model_validator(mode="after")
    def validate_segment_ordering(self) -> "Meeting":
        # Check segment sequences are strictly increasing
        for i in range(len(self.segments) - 1):
            if self.segments[i].sequence >= self.segments[i + 1].sequence:
                raise ValueError(
                    f"Segment sequence out of order: index {i} (seq {self.segments[i].sequence}) "
                    f"is not strictly less than index {i + 1} (seq {self.segments[i + 1].sequence})"
                )
        return self


# ------------------------------------------------------------------------------
# Extracted NLP Facts & Evidence Schemas
# ------------------------------------------------------------------------------


class ExtractedEntity(BaseSchema):
    """Named entity extracted from transcript text."""

    entity_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    entity_type: EntityType
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)
    segment_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedUtteranceClassification(BaseSchema):
    """Semantic classification of an utterance."""

    segment_id: str
    classes: list[UtteranceClass] = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedRelation(BaseSchema):
    """Typed relationship connecting entities or facts."""

    relation_id: str = Field(default_factory=lambda: str(uuid4()))
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationType
    meeting_id: str
    segment_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedEvent(BaseSchema):
    """Historical timeline change event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    occurred_at: datetime
    meeting_id: str
    subject_entity_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_segment_id: str | None = None

    @field_validator("occurred_at", mode="after")
    @classmethod
    def ensure_event_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class NormalizedTemporal(BaseSchema):
    """Normalized temporal expression resolved against meeting reference date."""

    text: str
    normalized_date: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    segment_id: str | None = None

    @field_validator("normalized_date", mode="after")
    @classmethod
    def ensure_temp_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class ExtractedDecision(BaseSchema):
    """Decision extracted from meeting with lifecycle state."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    subject: str = Field(..., min_length=1)
    status: DecisionStatus = DecisionStatus.PROPOSED
    rationale: str | None = None
    meeting_id: str
    evidence_segment_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExtractedCommitment(BaseSchema):
    """Action or commitment assigned with deadlines."""

    commitment_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(..., min_length=1)
    owner_id: str | None = None
    status: CommitmentStatus = CommitmentStatus.IDENTIFIED
    original_deadline: datetime | None = None
    current_deadline: datetime | None = None
    meeting_id: str
    evidence_segment_id: str | None = None


class ExtractedIssue(BaseSchema):
    """Organizational issue tracked across meetings."""

    issue_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(..., min_length=1)
    owner_id: str | None = None
    status: IssueStatus = IssueStatus.DETECTED
    first_detected_at: datetime = Field(default_factory=utc_now)
    last_mentioned_at: datetime = Field(default_factory=utc_now)
    resolution_meeting_id: str | None = None
    evidence_segment_id: str | None = None


# ------------------------------------------------------------------------------
# Evidence & Reasoning Schemas
# ------------------------------------------------------------------------------


class EvidenceItem(BaseSchema):
    """Provenance evidence linking a claim to source transcript and timestamp."""

    meeting_id: str
    segment_id: str
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)
    text_snapshot: str = Field(..., min_length=1)
    source_type: SourceType = SourceType.AUDIO_WAV


class ReasoningContext(BaseSchema):
    """Contextual evidence provided to the reasoner."""

    query_plan: dict[str, Any] = Field(default_factory=dict)
    retrieved_segments: list[TranscriptSegment] = Field(default_factory=list)
    graph_paths: list[dict[str, Any]] = Field(default_factory=list)
    timeline_events: list[ExtractedEvent] = Field(default_factory=list)


class AnswerWithAttribution(BaseSchema):
    """Grounded answer produced by reasoner with explicit evidence links."""

    question: str
    answer: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning_path: list[str] = Field(default_factory=list)

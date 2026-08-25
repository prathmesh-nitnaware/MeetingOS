from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 base class with standard JSON/JSONB type mapping."""

    type_annotation_map = {
        dict[str, Any]: JSON().with_variant(JSONB, "postgresql"),
        list[str]: JSON().with_variant(JSONB, "postgresql"),
    }


class MeetingModel(Base):
    """Relational table representing an ingested meeting."""

    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    meeting_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="audio/wav")
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="queued", index=True
    )
    model_pipeline_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    participants: Mapped[list["ParticipantModel"]] = relationship(
        "ParticipantModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    speakers: Mapped[list["SpeakerModel"]] = relationship(
        "SpeakerModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    segments: Mapped[list["TranscriptSegmentModel"]] = relationship(
        "TranscriptSegmentModel",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TranscriptSegmentModel.sequence",
    )
    jobs: Mapped[list["JobModel"]] = relationship(
        "JobModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["DecisionModel"]] = relationship(
        "DecisionModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    commitments: Mapped[list["CommitmentModel"]] = relationship(
        "CommitmentModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    issues: Mapped[list["IssueModel"]] = relationship(
        "IssueModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    events: Mapped[list["EventModel"]] = relationship(
        "EventModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    topics: Mapped[list["TopicModel"]] = relationship(
        "TopicModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["RelationshipModel"]] = relationship(
        "RelationshipModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    classifications: Mapped[list["UtteranceClassificationModel"]] = relationship(
        "UtteranceClassificationModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["EmbeddingModel"]] = relationship(
        "EmbeddingModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["EvidenceModel"]] = relationship(
        "EvidenceModel", back_populates="meeting", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_meetings_status_date", "processing_status", "meeting_date"),)


class ParticipantModel(Base):
    """Relational table representing meeting participants."""

    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="participants")


class SpeakerModel(Base):
    """Relational table mapping diarized speaker labels to participants."""

    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    speaker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="speakers")

    __table_args__ = (
        Index("ix_speakers_meeting_speaker", "meeting_id", "speaker_id", unique=True),
    )


class TranscriptSegmentModel(Base):
    """Relational table storing timestamped speaker transcript segments."""

    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="segments")

    __table_args__ = (
        Index("ix_transcript_segments_meeting_seq", "meeting_id", "sequence", unique=True),
        Index("ix_transcript_segments_times", "meeting_id", "start_time", "end_time"),
    )


class JobModel(Base):
    """Relational table tracking asynchronous processing job lifecycles."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str | None] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(100), nullable=False, default="initialized")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    meeting: Mapped[Optional["MeetingModel"]] = relationship("MeetingModel", back_populates="jobs")


class EntityModel(Base):
    """Relational table storing canonical entities."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aliases_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class MeetingEntityModel(Base):
    """Association table linking meetings to extracted entities."""

    __tablename__ = "meeting_entities"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_meeting_entities_unique", "meeting_id", "entity_id", unique=True),)


class TopicModel(Base):
    """Relational table storing meeting discussion topics."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="topics")


class DecisionModel(Base):
    """Relational table storing extracted decisions."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Approved", index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_segment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="decisions")


class CommitmentModel(Base):
    """Relational table storing extracted commitments and action items."""

    __tablename__ = "commitments"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="In Progress", index=True
    )
    original_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_segment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="commitments")


class IssueModel(Base):
    """Relational table storing extracted problems and issues."""

    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Detected", index=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_mentioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_meeting_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_segment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="issues")


class EventModel(Base):
    """Relational table storing chronological lifecycle events."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    subject_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence_segment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="events")


class RelationshipModel(Base):
    """Relational table storing extracted typed relations between entities."""

    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    segment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="relationships")


class UtteranceClassificationModel(Base):
    """Relational table storing utterance multi-label classifications."""

    __tablename__ = "utterance_classifications"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    classes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="classifications")


class EmbeddingModel(Base):
    """Relational table storing vector representations for semantic retrieval."""

    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="segment", index=True
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="mock-sentence-embedder"
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="embeddings")

    __table_args__ = (Index("ix_embeddings_source", "meeting_id", "source_type", "source_id"),)


class EvidenceModel(Base):
    """Relational table storing evidence records linking facts/claims to transcript sources."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="audio/wav")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meeting: Mapped["MeetingModel"] = relationship("MeetingModel", back_populates="evidence")

    __table_args__ = (Index("ix_evidence_segment", "meeting_id", "segment_id"),)

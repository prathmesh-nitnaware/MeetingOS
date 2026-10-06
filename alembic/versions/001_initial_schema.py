"""001_initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Meetings
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="audio/wav"),
        sa.Column(
            "processing_status",
            sa.String(length=50),
            nullable=False,
            server_default="queued",
            index=True,
        ),
        sa.Column(
            "model_pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("source_provider", sa.String(length=100), nullable=True, index=True),
        sa.Column("external_meeting_id", sa.String(length=255), nullable=True, index=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_meetings_status_date", "meetings", ["processing_status", "meeting_date"])
    op.create_index(
        "ix_meetings_external_id",
        "meetings",
        ["source_provider", "external_meeting_id"],
        unique=True,
    )

    # 2. Participants
    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
    )

    # 3. Speakers
    op.create_table(
        "speakers",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("speaker_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("canonical_entity_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_speakers_meeting_speaker", "speakers", ["meeting_id", "speaker_id"], unique=True
    )

    # 4. Transcript Segments
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("speaker_id", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_transcript_segments_meeting_seq",
        "transcript_segments",
        ["meeting_id", "sequence"],
        unique=True,
    )
    op.create_index(
        "ix_transcript_segments_times",
        "transcript_segments",
        ["meeting_id", "start_time", "end_time"],
    )

    # 5. Jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="queued", index=True
        ),
        sa.Column("stage", sa.String(length=100), nullable=False, server_default="initialized"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 6. Entities
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("aliases_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 7. Meeting Entities (Association)
    op.create_table(
        "meeting_entities",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entity_id",
            sa.String(length=100),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_meeting_entities_unique", "meeting_entities", ["meeting_id", "entity_id"], unique=True
    )

    # 8. Topics
    op.create_table(
        "topics",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 9. Decisions
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="Approved", index=True
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("evidence_segment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "model_name", sa.String(length=100), nullable=False, server_default="mock-nlp-model"
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 10. Commitments
    op.create_table(
        "commitments",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.String(length=100), nullable=True, index=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="In Progress", index=True
        ),
        sa.Column("original_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_segment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "model_name", sa.String(length=100), nullable=False, server_default="mock-nlp-model"
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 11. Issues
    op.create_table(
        "issues",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.String(length=100), nullable=True, index=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="Detected", index=True
        ),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_mentioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_meeting_id", sa.String(length=100), nullable=True),
        sa.Column("evidence_segment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "model_name", sa.String(length=100), nullable=False, server_default="mock-nlp-model"
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 12. Events
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("subject_entity_id", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("evidence_segment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "model_name",
            sa.String(length=100),
            nullable=False,
            server_default="mock-temporal-engine",
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 13. Relationships
    op.create_table(
        "relationships",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_entity_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("target_entity_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("relation_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("segment_id", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "model_name", sa.String(length=100), nullable=False, server_default="mock-nlp-model"
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 14. Utterance Classifications
    op.create_table(
        "utterance_classifications",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("segment_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("classes_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.95"),
        sa.Column(
            "model_name", sa.String(length=100), nullable=False, server_default="mock-nlp-model"
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 15. Embeddings
    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            server_default="segment",
            index=True,
        ),
        sa.Column("source_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding_json", sa.JSON(), nullable=False),
        sa.Column(
            "model_name",
            sa.String(length=100),
            nullable=False,
            server_default="mock-sentence-embedder",
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("pipeline_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_embeddings_source", "embeddings", ["meeting_id", "source_type", "source_id"]
    )

    # 16. Evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=100),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("segment_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text_snapshot", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="audio/wav"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_evidence_segment", "evidence", ["meeting_id", "segment_id"])

    # 17. Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("actor_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("action", sa.String(length=100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=False, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("evidence")
    op.drop_table("embeddings")
    op.drop_table("utterance_classifications")
    op.drop_table("relationships")
    op.drop_table("events")
    op.drop_table("issues")
    op.drop_table("commitments")
    op.drop_table("decisions")
    op.drop_table("topics")
    op.drop_table("meeting_entities")
    op.drop_table("entities")
    op.drop_table("jobs")
    op.drop_table("transcript_segments")
    op.drop_table("speakers")
    op.drop_table("participants")
    op.drop_table("meetings")

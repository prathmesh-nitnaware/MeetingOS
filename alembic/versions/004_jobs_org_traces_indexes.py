"""004_jobs_org_traces_indexes

Revision ID: 004_jobs_org_traces_indexes
Revises: 003_multitenant_core
Create Date: 2026-09-30 10:00:00.000000

- jobs.org_id so job status can be scoped to the owning organisation
- agent_traces table: persisted, organisation-scoped multi-agent traces
- indexes that the ORM models declare but earlier migrations never created
- connector meetings unique per organisation (was globally unique)
- tags existing timeline events by origin (NLP extraction vs. temporal reconciliation) so
  re-running extraction or reconciliation no longer deletes or duplicates the other's events
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_jobs_org_traces_indexes"
down_revision: str | None = "003_multitenant_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("org_id", sa.String(length=64), nullable=True))
    op.create_index("ix_jobs_org_id", "jobs", ["org_id"], unique=False)
    op.execute(
        "UPDATE jobs SET org_id = (SELECT meetings.org_id FROM meetings WHERE meetings.id = jobs.meeting_id) "
        "WHERE org_id IS NULL AND meeting_id IS NOT NULL"
    )

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_traces_org_id", "agent_traces", ["org_id"], unique=False)
    op.create_index("ix_agent_traces_created_at", "agent_traces", ["created_at"], unique=False)
    op.create_index(
        "ix_agent_traces_org_created", "agent_traces", ["org_id", "created_at"], unique=False
    )

    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"], unique=False)

    # External meetings are unique per organisation, not globally
    op.drop_index("ix_meetings_external_id", table_name="meetings")
    op.create_index(
        "ix_meetings_org_external_id",
        "meetings",
        ["org_id", "source_provider", "external_meeting_id"],
        unique=True,
    )

    op.create_index(
        "ix_organization_memberships_org_id", "organization_memberships", ["org_id"], unique=False
    )
    op.create_index(
        "ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False
    )

    has_text_key = (
        "(payload_json::jsonb ->> 'text') IS NOT NULL"
        if op.get_bind().dialect.name == "postgresql"
        else "json_extract(payload_json, '$.text') IS NOT NULL"
    )
    op.execute(
        "UPDATE events SET model_name = 'nlp-event-extractor' "
        f"WHERE model_name = 'mock-temporal-engine' AND {has_text_key}"
    )
    op.execute(
        "UPDATE events SET model_name = 'temporal-reconciler' WHERE model_name = 'mock-temporal-engine'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE events SET model_name = 'mock-temporal-engine' "
        "WHERE model_name IN ('nlp-event-extractor', 'temporal-reconciler')"
    )
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_org_id", table_name="organization_memberships")
    op.drop_index("ix_meetings_org_external_id", table_name="meetings")
    op.create_index(
        "ix_meetings_external_id",
        "meetings",
        ["source_provider", "external_meeting_id"],
        unique=True,
    )
    op.drop_index("ix_audit_logs_org_id", table_name="audit_logs")
    op.drop_index("ix_agent_traces_org_created", table_name="agent_traces")
    op.drop_index("ix_agent_traces_created_at", table_name="agent_traces")
    op.drop_index("ix_agent_traces_org_id", table_name="agent_traces")
    op.drop_table("agent_traces")
    op.drop_index("ix_jobs_org_id", table_name="jobs")
    op.drop_column("jobs", "org_id")

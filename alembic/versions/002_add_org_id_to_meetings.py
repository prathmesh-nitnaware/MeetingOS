"""002_add_org_id_to_meetings

Revision ID: 002_add_org_id_to_meetings
Revises: 001_initial_schema
Create Date: 2026-09-28 09:30:00.000000

Adds org_id column to meetings table for multi-tenant row-level isolation.
Existing rows are backfilled with 'org_legacy' sentinel.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_org_id_to_meetings'
down_revision: str | None = '001_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_ORG_ID = 'org_legacy'


def upgrade() -> None:
    op.add_column(
        'meetings',
        sa.Column('org_id', sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text('UPDATE meetings SET org_id = :oid WHERE org_id IS NULL').bindparams(oid=LEGACY_ORG_ID)
    )
    op.alter_column('meetings', 'org_id', nullable=False)
    op.create_index('ix_meetings_org_id', 'meetings', ['org_id'], unique=False)
    op.create_index('ix_meetings_org_id_date', 'meetings', ['org_id', 'meeting_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_meetings_org_id_date', table_name='meetings')
    op.drop_index('ix_meetings_org_id', table_name='meetings')
    op.drop_column('meetings', 'org_id')


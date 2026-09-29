"""003_multitenant_retention

Revision ID: 003_multitenant_retention
Revises: 002_add_org_id_to_meetings
Create Date: 2026-09-28 10:30:00.000000

Creates organizations, users, memberships, invitations, retention policies,
and adds soft deletion columns and audit log tenant isolation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003_multitenant_retention'
down_revision: str | None = '002_add_org_id_to_meetings'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Create organizations table
    if 'organizations' not in existing_tables:
        op.create_table(
            'organizations',
            sa.Column('id', sa.String(length=64), primary_key=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('slug', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
            sa.Column('allowed_domains', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
        op.create_index('ix_organizations_status', 'organizations', ['status'], unique=False)

    # 2. Create users table
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('full_name', sa.String(length=255), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Create organization_memberships table
    if 'organization_memberships' not in existing_tables:
        op.create_table(
            'organization_memberships',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.String(length=100), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint('org_id', 'user_id', name='uq_org_user_membership'),
        )
        op.create_index('ix_org_membership_role', 'organization_memberships', ['org_id', 'role'], unique=False)

    # 4. Create organization_invitations table
    if 'organization_invitations' not in existing_tables:
        op.create_table(
            'organization_invitations',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
            sa.Column('token_hash', sa.String(length=255), nullable=False),
            sa.Column('invited_by', sa.String(length=100), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_org_invitations_token_hash', 'organization_invitations', ['token_hash'], unique=True)
        op.create_index('ix_org_invitations_org_email', 'organization_invitations', ['org_id', 'email'], unique=False)

    # 5. Create retention_policies table
    if 'retention_policies' not in existing_tables:
        op.create_table(
            'retention_policies',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('meeting_retention_days', sa.Integer(), nullable=True),
            sa.Column('audio_retention_days', sa.Integer(), nullable=True),
            sa.Column('transcript_retention_days', sa.Integer(), nullable=True),
            sa.Column('memory_retention_days', sa.Integer(), nullable=True),
            sa.Column('auto_delete_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_retention_policies_org_id', 'retention_policies', ['org_id'], unique=True)

    # 6. Add soft-deletion columns to meetings table
    if 'meetings' in existing_tables:
        meeting_cols = {c['name'] for c in insp.get_columns('meetings')}
        if 'deleted_at' not in meeting_cols:
            op.add_column('meetings', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
            op.create_index('ix_meetings_deleted_at', 'meetings', ['deleted_at'], unique=False)
        if 'deleted_by' not in meeting_cols:
            op.add_column('meetings', sa.Column('deleted_by', sa.String(length=100), nullable=True))

    # 7. Add org_id to audit_logs table
    if 'audit_logs' in existing_tables:
        audit_cols = {c['name'] for c in insp.get_columns('audit_logs')}
        if 'org_id' not in audit_cols:
            op.add_column('audit_logs', sa.Column('org_id', sa.String(length=64), nullable=True))
            op.execute(sa.text("UPDATE audit_logs SET org_id = 'org_dev' WHERE org_id IS NULL"))
            op.alter_column('audit_logs', 'org_id', nullable=False)
            op.create_index('ix_audit_org_timestamp', 'audit_logs', ['org_id', 'timestamp'], unique=False)

    # 8. Seed default organizations for existing development data
    op.execute(
        sa.text("""
            INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
            VALUES ('org_dev', 'Development Workspace', 'dev', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """)
    )
    op.execute(
        sa.text("""
            INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
            VALUES ('org_beta', 'BetaCorp Workspace', 'betacorp', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'audit_logs' in existing_tables:
        audit_cols = {c['name'] for c in insp.get_columns('audit_logs')}
        if 'org_id' in audit_cols:
            op.drop_index('ix_audit_org_timestamp', table_name='audit_logs')
            op.drop_column('audit_logs', 'org_id')

    if 'meetings' in existing_tables:
        meeting_cols = {c['name'] for c in insp.get_columns('meetings')}
        if 'deleted_at' in meeting_cols:
            op.drop_index('ix_meetings_deleted_at', table_name='meetings')
            op.drop_column('meetings', 'deleted_at')
        if 'deleted_by' in meeting_cols:
            op.drop_column('meetings', 'deleted_by')

    if 'retention_policies' in existing_tables:
        op.drop_table('retention_policies')
    if 'organization_invitations' in existing_tables:
        op.drop_table('organization_invitations')
    if 'organization_memberships' in existing_tables:
        op.drop_table('organization_memberships')
    if 'users' in existing_tables:
        op.drop_table('users')
    if 'organizations' in existing_tables:
        op.drop_table('organizations')

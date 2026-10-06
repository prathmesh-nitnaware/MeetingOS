"""Development-only fixtures that back the hard-coded dev tokens with real database rows.

Without these rows, features that reference the acting user or organisation (invitations,
memberships, retention policies) fail with foreign-key errors when using dev tokens.
Only called when ``settings.dev_auth_enabled`` is true.
"""

import logging

from apps.api.auth import DEV_ORGANIZATIONS, DEV_TOKENS
from packages.memory.models import OrganizationMembershipModel, OrganizationModel, UserModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def ensure_dev_fixtures(session: AsyncSession) -> None:
    """Idempotently create the dev organisations, users and memberships."""
    for org_id, (name, slug) in DEV_ORGANIZATIONS.items():
        if await session.get(OrganizationModel, org_id) is None:
            slug_taken = (
                await session.execute(
                    select(OrganizationModel.id).where(OrganizationModel.slug == slug)
                )
            ).first()
            session.add(
                OrganizationModel(
                    id=org_id,
                    name=name,
                    slug=f"{slug}-{org_id}" if slug_taken else slug,
                    status="active",
                    allowed_domains=[],
                )
            )
    await session.flush()

    for identity in DEV_TOKENS.values():
        if await session.get(UserModel, identity.user_id) is None:
            email_taken = (
                await session.execute(select(UserModel.id).where(UserModel.email == identity.email))
            ).first()
            if email_taken:
                logger.warning(
                    "Dev user %s not created: email %s already belongs to another account.",
                    identity.user_id,
                    identity.email,
                )
                continue
            session.add(
                UserModel(
                    id=identity.user_id,
                    email=identity.email or f"{identity.user_id}@meetingos.local",
                    full_name=identity.full_name or identity.user_id,
                    password_hash=None,
                    is_active=True,
                )
            )
            await session.flush()

        membership = (
            await session.execute(
                select(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.org_id == identity.org_id,
                    OrganizationMembershipModel.user_id == identity.user_id,
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            session.add(
                OrganizationMembershipModel(
                    org_id=identity.org_id,
                    user_id=identity.user_id,
                    role=identity.role,
                    status="active",
                )
            )
    await session.flush()

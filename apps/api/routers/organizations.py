import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.auth import (
    ROLE_RANK,
    UserIdentity,
    require_permission,
    require_viewer,
)
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from packages.memory.database import get_db_session
from packages.memory.models import (
    AuditLogModel,
    MeetingModel,
    OrganizationInvitationModel,
    OrganizationMembershipModel,
    OrganizationModel,
    RetentionPolicyModel,
    UserModel,
    utc_now,
)
from packages.memory.retention import RetentionService
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/organizations", tags=["Organization Administration"])


class OrganizationDetail(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    allowed_domains: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    total_members: int = 1
    total_meetings: int = 0


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    allowed_domains: list[str] | None = None


class MemberItem(BaseModel):
    membership_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_RE.match(cleaned):
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("role")
    @classmethod
    def check_role(cls, value: str) -> str:
        role = value.strip().lower()
        if role not in ROLE_RANK:
            raise ValueError(f"Role must be one of: {', '.join(ROLE_RANK)}.")
        return role


class InvitationItem(BaseModel):
    invitation_id: str
    email: str
    role: str
    invited_by: str
    expires_at: datetime
    created_at: datetime
    invitation_token: str | None = None


class RetentionPolicySchema(BaseModel):
    meeting_retention_days: int | None = Field(default=None, ge=1)
    audio_retention_days: int | None = Field(default=None, ge=1)
    transcript_retention_days: int | None = Field(default=None, ge=1)
    memory_retention_days: int | None = Field(default=None, ge=1)
    auto_delete_enabled: bool = False


@router.get("/current", response_model=OrganizationDetail)
async def get_current_organization(
    user: UserIdentity = Depends(require_viewer),
) -> OrganizationDetail:
    """Retrieve details, status, and summary metrics of the current organisation."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(OrganizationModel).where(OrganizationModel.id == user.org_id)
        org = (await session.execute(stmt)).scalar_one_or_none()

        # Count active members and meetings
        mem_count = (
            await session.execute(
                select(func.count(OrganizationMembershipModel.id)).where(
                    OrganizationMembershipModel.org_id == user.org_id,
                    OrganizationMembershipModel.status == "active",
                )
            )
        ).scalar() or 0

        meet_count = (
            await session.execute(
                select(func.count(MeetingModel.id)).where(
                    MeetingModel.org_id == user.org_id,
                    MeetingModel.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        if not org:
            # Tenant without an organizations row (e.g. dev tokens before fixtures are seeded)
            return OrganizationDetail(
                id=user.org_id,
                name="Development Workspace",
                slug=user.org_id,
                status="active",
                allowed_domains=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                total_members=max(mem_count, 1),
                total_meetings=meet_count,
            )

        return OrganizationDetail(
            id=org.id,
            name=org.name,
            slug=org.slug,
            status=org.status,
            allowed_domains=org.allowed_domains,
            created_at=org.created_at,
            updated_at=org.updated_at,
            total_members=mem_count,
            total_meetings=meet_count,
        )


@router.patch("/current", response_model=OrganizationDetail)
async def update_current_organization(
    request: UpdateOrganizationRequest,
    user: UserIdentity = Depends(require_permission("organization.update")),
) -> OrganizationDetail:
    """Update organisation settings (Admin or Owner only)."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(OrganizationModel).where(OrganizationModel.id == user.org_id)
        org = (await session.execute(stmt)).scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found.")

        if request.name is not None:
            org.name = request.name.strip()
        if request.allowed_domains is not None:
            org.allowed_domains = request.allowed_domains

        org.updated_at = utc_now()
        await session.commit()
        return await get_current_organization(user)


@router.get("/current/members", response_model=list[MemberItem])
async def list_members(
    user: UserIdentity = Depends(require_permission("members.read")),
) -> list[MemberItem]:
    """List all users belonging to the current organisation."""
    async with get_db_session(settings.database_url) as session:
        stmt = (
            select(OrganizationMembershipModel, UserModel)
            .join(UserModel, UserModel.id == OrganizationMembershipModel.user_id)
            .where(OrganizationMembershipModel.org_id == user.org_id)
            .order_by(OrganizationMembershipModel.created_at.asc())
        )
        rows = (await session.execute(stmt)).all()

        members = []
        for mem, u in rows:
            members.append(
                MemberItem(
                    membership_id=mem.id,
                    user_id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    role=mem.role,
                    status=mem.status,
                    created_at=mem.created_at,
                )
            )
        return members


@router.post("/current/invitations", response_model=InvitationItem)
async def invite_member(
    request: InviteMemberRequest,
    user: UserIdentity = Depends(require_permission("members.invite")),
) -> InvitationItem:
    """Invite a new member to join this organisation.

    Nobody can grant a role above their own (an admin cannot create an owner).
    """
    if ROLE_RANK[request.role] > ROLE_RANK.get(user.role, -1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: a {user.role} cannot invite someone as {request.role}.",
        )
    email_clean = request.email
    raw_token = f"inv_{uuid.uuid4().hex}"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires = utc_now() + timedelta(days=7)

    async with get_db_session(settings.database_url) as session:
        inv = OrganizationInvitationModel(
            id=str(uuid.uuid4()),
            org_id=user.org_id,
            email=email_clean,
            role=request.role,
            token_hash=token_hash,
            invited_by=user.user_id,
            expires_at=expires,
        )
        session.add(inv)

        # Audit log
        session.add(
            AuditLogModel(
                org_id=user.org_id,
                actor_id=user.user_id,
                action="member.invited",
                resource_type="invitation",
                resource_id=inv.id,
                outcome="succeeded",
                metadata_json={"email": email_clean, "role": request.role},
            )
        )
        await session.commit()

        return InvitationItem(
            invitation_id=inv.id,
            email=inv.email,
            role=inv.role,
            invited_by=inv.invited_by,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            invitation_token=raw_token,
        )


@router.delete("/current/members/{target_user_id}", response_model=dict[str, Any])
async def remove_member(
    target_user_id: str,
    user: UserIdentity = Depends(require_permission("members.remove")),
) -> dict[str, Any]:
    """Remove a user from this organisation."""
    if target_user_id == user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization.",
        )

    async with get_db_session(settings.database_url) as session:
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.org_id == user.org_id,
            OrganizationMembershipModel.user_id == target_user_id,
        )
        mem = (await session.execute(stmt)).scalar_one_or_none()
        if not mem:
            raise HTTPException(status_code=404, detail="Member not found.")

        if mem.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove an organization Owner.",
            )
        if ROLE_RANK.get(mem.role, 0) > ROLE_RANK.get(user.role, -1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove a member whose role is higher than yours.",
            )

        await session.delete(mem)
        session.add(
            AuditLogModel(
                org_id=user.org_id,
                actor_id=user.user_id,
                action="member.removed",
                resource_type="user",
                resource_id=target_user_id,
                outcome="succeeded",
            )
        )
        await session.commit()
        return {"status": "succeeded", "removed_user_id": target_user_id}


@router.get("/current/retention", response_model=RetentionPolicySchema)
async def get_retention_policy(
    user: UserIdentity = Depends(require_permission("organization.read")),
) -> RetentionPolicySchema:
    """Get the organization's data retention configuration."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.org_id == user.org_id)
        policy = (await session.execute(stmt)).scalar_one_or_none()
        if not policy:
            return RetentionPolicySchema()
        return RetentionPolicySchema(
            meeting_retention_days=policy.meeting_retention_days,
            audio_retention_days=policy.audio_retention_days,
            transcript_retention_days=policy.transcript_retention_days,
            memory_retention_days=policy.memory_retention_days,
            auto_delete_enabled=policy.auto_delete_enabled,
        )


@router.put("/current/retention", response_model=RetentionPolicySchema)
async def update_retention_policy(
    policy_data: RetentionPolicySchema,
    user: UserIdentity = Depends(require_permission("organization.update")),
) -> RetentionPolicySchema:
    """Set or update data retention policies (Admin/Owner only)."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.org_id == user.org_id)
        policy = (await session.execute(stmt)).scalar_one_or_none()
        if not policy:
            policy = RetentionPolicyModel(
                id=str(uuid.uuid4()),
                org_id=user.org_id,
            )
            session.add(policy)

        policy.meeting_retention_days = policy_data.meeting_retention_days
        policy.audio_retention_days = policy_data.audio_retention_days
        policy.transcript_retention_days = policy_data.transcript_retention_days
        policy.memory_retention_days = policy_data.memory_retention_days
        policy.auto_delete_enabled = policy_data.auto_delete_enabled
        policy.updated_at = utc_now()

        session.add(
            AuditLogModel(
                org_id=user.org_id,
                actor_id=user.user_id,
                action="retention_policy.updated",
                resource_type="retention_policy",
                resource_id=policy.id,
                outcome="succeeded",
                metadata_json=policy_data.model_dump(),
            )
        )
        await session.commit()
        return policy_data


@router.post("/current/retention/preview", response_model=dict[str, Any])
async def preview_retention_cleanup(
    user: UserIdentity = Depends(require_permission("organization.read")),
) -> dict[str, Any]:
    """Safe, non-destructive preview of meetings and records eligible for retention cleanup."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.org_id == user.org_id)
        policy = (await session.execute(stmt)).scalar_one_or_none()

        service = RetentionService(session, org_id=user.org_id)
        results = await service.run_cleanup(
            meeting_days=policy.meeting_retention_days if policy else None,
            transcript_days=policy.transcript_retention_days if policy else None,
            audio_days=policy.audio_retention_days if policy else None,
            evidence_days=policy.memory_retention_days if policy else None,
            dry_run=True,
            actor_id=user.user_id,
        )
        return {
            "status": "preview",
            "org_id": user.org_id,
            "policy_configured": policy is not None,
            "eligible_for_deletion": results,
        }

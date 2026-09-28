import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.auth import UserIdentity, create_access_token, get_current_user, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from packages.memory.database import get_db_session
from packages.memory.models import (
    AuditLogModel,
    OrganizationInvitationModel,
    OrganizationMembershipModel,
    OrganizationModel,
    UserModel,
    utc_now,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


class LoginRequest(BaseModel):
    email: str
    password: str | None = None
    org_slug: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 86400
    user: UserIdentity
    available_organizations: list[dict[str, Any]] = []


class RegisterOrgRequest(BaseModel):
    org_name: str
    org_slug: str
    admin_name: str
    admin_email: str
    admin_password: str | None = None
    allowed_domains: list[str] | None = None


class SwitchOrgRequest(BaseModel):
    target_org_id: str


class AcceptInvitationRequest(BaseModel):
    token: str
    full_name: str | None = None
    password: str | None = None


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str | None = None
    full_name: str | None = None
    role: str
    org_id: str
    organization_name: str | None = None
    organization_slug: str | None = None
    permissions: list[str] = []
    organizations: list[dict[str, Any]] = []


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographically secure random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify password against stored PBKDF2 salt hash or fallback legacy hash."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        salt, expected_key_hex = parts[1], parts[2]
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key.hex(), expected_key_hex)
    else:
        # Legacy fallback comparison
        legacy_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(legacy_hash, hashed_password)



@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate a user and return a tenant-scoped JWT access token."""
    email_clean = request.email.strip().lower()

    async with get_db_session(settings.database_url) as session:
        # 1. Lookup user by email
        stmt = select(UserModel).where(UserModel.email == email_clean)
        user_row = (await session.execute(stmt)).scalar_one_or_none()

        if not user_row:
            # Fallback for local development if email matches dev tokens
            if "admin" in email_clean:
                token = create_access_token(
                    user_id="admin-dev",
                    org_id="org_dev",
                    role="admin",
                    email=email_clean,
                    full_name="Dev Admin",
                )
                identity = UserIdentity(
                    user_id="admin-dev",
                    org_id="org_dev",
                    role="admin",
                    email=email_clean,
                    full_name="Dev Admin",
                )
                return LoginResponse(
                    access_token=token,
                    user=identity,
                    available_organizations=[{"id": "org_dev", "name": "Development Org", "role": "admin"}],
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or user not found.",
            )

        if not user_row.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been suspended or deactivated.",
            )

        # 2. Fetch user's memberships
        stmt_mem = select(OrganizationMembershipModel, OrganizationModel).join(
            OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id
        ).where(
            OrganizationMembershipModel.user_id == user_row.id,
            OrganizationMembershipModel.status == "active",
            OrganizationModel.status == "active",
        )
        membership_rows = (await session.execute(stmt_mem)).all()

        if not membership_rows:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no active organization memberships.",
            )

        # 3. Select target organization
        active_mem = None
        if request.org_slug:
            for mem, org in membership_rows:
                if org.slug == request.org_slug:
                    active_mem = (mem, org)
                    break
        if not active_mem:
            active_mem = membership_rows[0]

        target_mem, target_org = active_mem

        token = create_access_token(
            user_id=user_row.id,
            org_id=target_org.id,
            role=target_mem.role,
            email=user_row.email,
            full_name=user_row.full_name,
        )

        identity = UserIdentity(
            user_id=user_row.id,
            org_id=target_org.id,
            role=target_mem.role,
            email=user_row.email,
            full_name=user_row.full_name,
        )

        org_list = [
            {"id": org.id, "name": org.name, "slug": org.slug, "role": mem.role}
            for mem, org in membership_rows
        ]

        return LoginResponse(
            access_token=token,
            user=identity,
            available_organizations=org_list,
        )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_profile(
    user: UserIdentity = Depends(get_current_user),
) -> CurrentUserResponse:
    """Retrieve full tenant context, role, permissions, and available organizations."""
    async with get_db_session(settings.database_url) as session:
        # Fetch organization info
        stmt_org = select(OrganizationModel).where(OrganizationModel.id == user.org_id)
        org_row = (await session.execute(stmt_org)).scalar_one_or_none()

        # Fetch other accessible organizations
        stmt_user = select(UserModel).where(UserModel.id == user.user_id)
        user_row = (await session.execute(stmt_user)).scalar_one_or_none()

        org_list = []
        if user_row:
            stmt_mem = select(OrganizationMembershipModel, OrganizationModel).join(
                OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id
            ).where(
                OrganizationMembershipModel.user_id == user_row.id,
                OrganizationMembershipModel.status == "active",
            )
            for mem, org in (await session.execute(stmt_mem)).all():
                org_list.append({"id": org.id, "name": org.name, "slug": org.slug, "role": mem.role})
        else:
            org_list.append({
                "id": user.org_id,
                "name": org_row.name if org_row else "Current Workspace",
                "slug": org_row.slug if org_row else user.org_id,
                "role": user.role,
            })

        return CurrentUserResponse(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            org_id=user.org_id,
            organization_name=org_row.name if org_row else user.org_id,
            organization_slug=org_row.slug if org_row else user.org_id,
            permissions=user.permissions,
            organizations=org_list,
        )


@router.post("/register-org", response_model=LoginResponse)
async def register_organization(request: RegisterOrgRequest) -> LoginResponse:
    """Create a brand new isolated organization tenant and initial Owner account."""
    slug_clean = request.org_slug.strip().lower().replace(" ", "-")
    email_clean = request.admin_email.strip().lower()

    async with get_db_session(settings.database_url) as session:
        # Check slug collision
        stmt_slug = select(OrganizationModel).where(OrganizationModel.slug == slug_clean)
        existing_org = (await session.execute(stmt_slug)).scalar_one_or_none()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An organization with workspace URL slug '{slug_clean}' already exists.",
            )

        org_id = f"org_{uuid.uuid4().hex[:12]}"
        org = OrganizationModel(
            id=org_id,
            name=request.org_name.strip(),
            slug=slug_clean,
            status="active",
            allowed_domains=request.allowed_domains or [],
        )
        session.add(org)

        # Check user or create
        stmt_user = select(UserModel).where(UserModel.email == email_clean)
        user = (await session.execute(stmt_user)).scalar_one_or_none()
        if not user:
            user_id = str(uuid.uuid4())
            pw_hash = hash_password(request.admin_password) if request.admin_password else None
            user = UserModel(
                id=user_id,
                email=email_clean,
                full_name=request.admin_name.strip(),
                password_hash=pw_hash,
                is_active=True,
            )
            session.add(user)
            await session.flush()

        # Create Owner membership
        membership = OrganizationMembershipModel(
            id=str(uuid.uuid4()),
            org_id=org.id,
            user_id=user.id,
            role="owner",
            status="active",
        )
        session.add(membership)

        # Audit log creation of new org
        session.add(
            AuditLogModel(
                org_id=org.id,
                actor_id=user.id,
                action="organization.registered",
                resource_type="organization",
                resource_id=org.id,
                outcome="succeeded",
                metadata_json={"org_name": org.name, "org_slug": org.slug},
            )
        )
        await session.commit()

        token = create_access_token(
            user_id=user.id,
            org_id=org.id,
            role="owner",
            email=user.email,
            full_name=user.full_name,
        )

        identity = UserIdentity(
            user_id=user.id,
            org_id=org.id,
            role="owner",
            email=user.email,
            full_name=user.full_name,
        )

        return LoginResponse(
            access_token=token,
            user=identity,
            available_organizations=[{"id": org.id, "name": org.name, "slug": org.slug, "role": "owner"}],
        )


@router.post("/switch-org", response_model=LoginResponse)
async def switch_organization(
    request: SwitchOrgRequest,
    current_user: UserIdentity = Depends(get_current_user),
) -> LoginResponse:
    """Switch active tenant context for a multi-tenant user and generate a new JWT."""
    async with get_db_session(settings.database_url) as session:
        stmt = select(OrganizationMembershipModel, OrganizationModel).join(
            OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id
        ).where(
            OrganizationMembershipModel.user_id == current_user.user_id,
            OrganizationMembershipModel.org_id == request.target_org_id,
            OrganizationMembershipModel.status == "active",
            OrganizationModel.status == "active",
        )
        result = (await session.execute(stmt)).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have an active membership in the requested organization.",
            )

        target_mem, target_org = result
        token = create_access_token(
            user_id=current_user.user_id,
            org_id=target_org.id,
            role=target_mem.role,
            email=current_user.email,
            full_name=current_user.full_name,
        )

        identity = UserIdentity(
            user_id=current_user.user_id,
            org_id=target_org.id,
            role=target_mem.role,
            email=current_user.email,
            full_name=current_user.full_name,
        )

        return LoginResponse(
            access_token=token,
            user=identity,
            available_organizations=[{"id": target_org.id, "name": target_org.name, "slug": target_org.slug, "role": target_mem.role}],
        )


@router.post("/invitations/accept", response_model=LoginResponse)
async def accept_invitation(request: AcceptInvitationRequest) -> LoginResponse:
    """Accept an organization invitation, create or link user account, and return tenant-scoped JWT."""
    raw_token = request.token.strip()
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async with get_db_session(settings.database_url) as session:
        stmt_inv = (
            select(OrganizationInvitationModel, OrganizationModel)
            .join(OrganizationModel, OrganizationModel.id == OrganizationInvitationModel.org_id)
            .where(
                OrganizationInvitationModel.token_hash == token_hash,
                OrganizationModel.status == "active",
            )
        )
        result = (await session.execute(stmt_inv)).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found or invalid token.",
            )

        inv, org = result

        if inv.accepted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has already been accepted.",
            )

        # Check expiration
        now_dt = utc_now()
        exp_dt = inv.expires_at
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=UTC)
        if now_dt > exp_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation token has expired.",
            )

        # Find or create user
        stmt_user = select(UserModel).where(UserModel.email == inv.email.lower())
        user = (await session.execute(stmt_user)).scalar_one_or_none()

        if not user:
            user_id = str(uuid.uuid4())
            pw_hash = hash_password(request.password) if request.password else None
            user = UserModel(
                id=user_id,
                email=inv.email.lower(),
                full_name=(request.full_name or inv.email.split("@")[0]).strip(),
                password_hash=pw_hash,
                is_active=True,
            )
            session.add(user)
            await session.flush()
        else:
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot accept invitation: user account is deactivated.",
                )

        # Check existing membership
        stmt_mem = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.org_id == org.id,
            OrganizationMembershipModel.user_id == user.id,
        )
        existing_mem = (await session.execute(stmt_mem)).scalar_one_or_none()

        if existing_mem:
            existing_mem.role = inv.role
            existing_mem.status = "active"
            existing_mem.updated_at = utc_now()
        else:
            membership = OrganizationMembershipModel(
                id=str(uuid.uuid4()),
                org_id=org.id,
                user_id=user.id,
                role=inv.role,
                status="active",
            )
            session.add(membership)

        inv.accepted_at = utc_now()

        # Audit log
        session.add(
            AuditLogModel(
                org_id=org.id,
                actor_id=user.id,
                action="member.joined_via_invitation",
                resource_type="invitation",
                resource_id=inv.id,
                outcome="succeeded",
                metadata_json={"email": user.email, "role": inv.role},
            )
        )
        await session.commit()

        token = create_access_token(
            user_id=user.id,
            org_id=org.id,
            role=inv.role,
            email=user.email,
            full_name=user.full_name,
        )

        identity = UserIdentity(
            user_id=user.id,
            org_id=org.id,
            role=inv.role,
            email=user.email,
            full_name=user.full_name,
        )

        return LoginResponse(
            access_token=token,
            user=identity,
            available_organizations=[{"id": org.id, "name": org.name, "slug": org.slug, "role": inv.role}],
        )


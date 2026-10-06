import hashlib
import re
import secrets
import uuid
from datetime import UTC
from typing import Any

from apps.api.auth import (
    DEV_TOKENS,
    ROLE_PERMISSIONS,
    UserIdentity,
    create_access_token,
    get_current_user,
)
from apps.api.config import settings
from apps.api.rate_limiter import rate_limit
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
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
MIN_PASSWORD_LENGTH = 8
PBKDF2_ITERATIONS = 600_000
LEGACY_PBKDF2_ITERATIONS = 100_000
INVALID_CREDENTIALS = "Invalid email or password."

auth_rate_limit = rate_limit("auth", lambda: settings.rate_limit_login_per_min)


def _validate_email(value: str) -> str:
    cleaned = value.strip().lower()
    if not EMAIL_RE.match(cleaned):
        raise ValueError("Enter a valid email address.")
    return cleaned


def _validate_new_password(value: str | None) -> str | None:
    if value is not None and len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    return value


class LoginRequest(BaseModel):
    email: str
    password: str = ""
    org_slug: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 86400
    user: UserIdentity
    available_organizations: list[dict[str, Any]] = []


class RegisterOrgRequest(BaseModel):
    org_name: str = Field(min_length=1, max_length=255)
    org_slug: str
    admin_name: str = Field(min_length=1, max_length=255)
    admin_email: str
    admin_password: str | None = None
    allowed_domains: list[str] | None = None

    @field_validator("admin_email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("admin_password")
    @classmethod
    def check_password(cls, value: str | None) -> str | None:
        return _validate_new_password(value)


class SwitchOrgRequest(BaseModel):
    target_org_id: str


class AcceptInvitationRequest(BaseModel):
    token: str
    full_name: str | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None) -> str | None:
        return _validate_new_password(value)


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


class DevPersona(BaseModel):
    token: str
    label: str
    org_id: str
    role: str


class AuthConfigResponse(BaseModel):
    dev_auth_enabled: bool
    dev_personas: list[DevPersona] = []


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a random salt (iterations stored in the hash)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a password against a stored PBKDF2 hash (current or older formats)."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 4:
            try:
                iterations = int(parts[1])
            except ValueError:
                return False
            salt, expected_key_hex = parts[2], parts[3]
        elif len(parts) == 3:
            iterations, salt, expected_key_hex = LEGACY_PBKDF2_ITERATIONS, parts[1], parts[2]
        else:
            return False
        key = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return secrets.compare_digest(key.hex(), expected_key_hex)
    # Legacy unsalted SHA-256 hashes from early development builds
    legacy_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy_hash, hashed_password)


def _identity(user: UserModel, org_id: str, role: str) -> UserIdentity:
    return UserIdentity(
        user_id=user.id,
        org_id=org_id,
        role=role,
        email=user.email,
        full_name=user.full_name,
        permissions=sorted(ROLE_PERMISSIONS.get(role, set())),
    )


def _token_response(
    user: UserModel, org_id: str, role: str, orgs: list[dict[str, Any]]
) -> LoginResponse:
    return LoginResponse(
        access_token=create_access_token(
            user_id=user.id,
            org_id=org_id,
            role=role,
            email=user.email,
            full_name=user.full_name,
        ),
        expires_in_seconds=settings.access_token_ttl_minutes * 60,
        user=_identity(user, org_id, role),
        available_organizations=orgs,
    )


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config() -> AuthConfigResponse:
    """Public sign-in configuration. Development personas are only listed in dev/test."""
    if not settings.dev_auth_enabled:
        return AuthConfigResponse(dev_auth_enabled=False)
    personas = [
        DevPersona(
            token=token,
            label=f"{identity.full_name} ({identity.role}, {identity.org_id})",
            org_id=identity.org_id,
            role=identity.role,
        )
        for token, identity in DEV_TOKENS.items()
    ]
    return AuthConfigResponse(dev_auth_enabled=True, dev_personas=personas)


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(auth_rate_limit)])
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate a user with email + password and return a tenant-scoped JWT access token."""
    email_clean = request.email.strip().lower()

    async with get_db_session(settings.database_url) as session:
        user_row = (
            await session.execute(select(UserModel).where(UserModel.email == email_clean))
        ).scalar_one_or_none()

        # Same message for unknown users and wrong passwords to avoid account enumeration
        if not user_row or not verify_password(request.password, user_row.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS
            )

        if not user_row.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been suspended or deactivated.",
            )

        membership_rows = (
            await session.execute(
                select(OrganizationMembershipModel, OrganizationModel)
                .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id)
                .where(
                    OrganizationMembershipModel.user_id == user_row.id,
                    OrganizationMembershipModel.status == "active",
                    OrganizationModel.status == "active",
                )
            )
        ).all()

        if not membership_rows:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no active organization memberships.",
            )

        active_mem = None
        if request.org_slug:
            for mem, org in membership_rows:
                if org.slug == request.org_slug:
                    active_mem = (mem, org)
                    break
        if not active_mem:
            active_mem = membership_rows[0]
        target_mem, target_org = active_mem

        org_list = [
            {"id": org.id, "name": org.name, "slug": org.slug, "role": mem.role}
            for mem, org in membership_rows
        ]
        return _token_response(user_row, target_org.id, target_mem.role, org_list)


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_profile(
    user: UserIdentity = Depends(get_current_user),
) -> CurrentUserResponse:
    """Retrieve full tenant context, role, permissions, and available organizations."""
    async with get_db_session(settings.database_url) as session:
        org_row = await session.get(OrganizationModel, user.org_id)
        user_row = await session.get(UserModel, user.user_id)

        org_list = []
        if user_row:
            stmt_mem = (
                select(OrganizationMembershipModel, OrganizationModel)
                .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id)
                .where(
                    OrganizationMembershipModel.user_id == user_row.id,
                    OrganizationMembershipModel.status == "active",
                )
            )
            for mem, org in (await session.execute(stmt_mem)).all():
                org_list.append(
                    {"id": org.id, "name": org.name, "slug": org.slug, "role": mem.role}
                )
        else:
            org_list.append(
                {
                    "id": user.org_id,
                    "name": org_row.name if org_row else "Current Workspace",
                    "slug": org_row.slug if org_row else user.org_id,
                    "role": user.role,
                }
            )

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


@router.post("/register-org", response_model=LoginResponse, dependencies=[Depends(auth_rate_limit)])
async def register_organization(request: RegisterOrgRequest) -> LoginResponse:
    """Create a new isolated organization tenant and its initial Owner account.

    If the email already belongs to an account, the correct password for that account is
    required; otherwise anyone could obtain a token for someone else's user ID.
    """
    slug_clean = request.org_slug.strip().lower().replace(" ", "-")
    if not SLUG_RE.match(slug_clean):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workspace URL may only contain lowercase letters, digits and hyphens (max 64).",
        )
    email_clean = request.admin_email

    async with get_db_session(settings.database_url) as session:
        existing_org = (
            await session.execute(
                select(OrganizationModel).where(OrganizationModel.slug == slug_clean)
            )
        ).scalar_one_or_none()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An organization with workspace URL slug '{slug_clean}' already exists.",
            )

        user = (
            await session.execute(select(UserModel).where(UserModel.email == email_clean))
        ).scalar_one_or_none()
        if user:
            if not request.admin_password or not verify_password(
                request.admin_password, user.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists. Enter that account's password to create another organization.",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This user account has been suspended or deactivated.",
                )
        else:
            if not request.admin_password:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"A password of at least {MIN_PASSWORD_LENGTH} characters is required.",
                )
            user = UserModel(
                id=str(uuid.uuid4()),
                email=email_clean,
                full_name=request.admin_name.strip(),
                password_hash=hash_password(request.admin_password),
                is_active=True,
            )
            session.add(user)

        org = OrganizationModel(
            id=f"org_{uuid.uuid4().hex[:12]}",
            name=request.org_name.strip(),
            slug=slug_clean,
            status="active",
            allowed_domains=request.allowed_domains or [],
        )
        session.add(org)
        await session.flush()

        session.add(
            OrganizationMembershipModel(
                id=str(uuid.uuid4()),
                org_id=org.id,
                user_id=user.id,
                role="owner",
                status="active",
            )
        )
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

        return _token_response(
            user,
            org.id,
            "owner",
            [{"id": org.id, "name": org.name, "slug": org.slug, "role": "owner"}],
        )


@router.post("/switch-org", response_model=LoginResponse)
async def switch_organization(
    request: SwitchOrgRequest,
    current_user: UserIdentity = Depends(get_current_user),
) -> LoginResponse:
    """Switch active tenant context for a multi-tenant user and generate a new JWT."""
    async with get_db_session(settings.database_url) as session:
        result = (
            await session.execute(
                select(OrganizationMembershipModel, OrganizationModel, UserModel)
                .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id)
                .join(UserModel, UserModel.id == OrganizationMembershipModel.user_id)
                .where(
                    OrganizationMembershipModel.user_id == current_user.user_id,
                    OrganizationMembershipModel.org_id == request.target_org_id,
                    OrganizationMembershipModel.status == "active",
                    OrganizationModel.status == "active",
                    UserModel.is_active.is_(True),
                )
            )
        ).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have an active membership in the requested organization.",
            )

        target_mem, target_org, user_row = result
        return _token_response(
            user_row,
            target_org.id,
            target_mem.role,
            [
                {
                    "id": target_org.id,
                    "name": target_org.name,
                    "slug": target_org.slug,
                    "role": target_mem.role,
                }
            ],
        )


@router.post(
    "/invitations/accept", response_model=LoginResponse, dependencies=[Depends(auth_rate_limit)]
)
async def accept_invitation(request: AcceptInvitationRequest) -> LoginResponse:
    """Accept an organization invitation, create or link user account, and return tenant-scoped JWT."""
    token_hash = hashlib.sha256(request.token.strip().encode("utf-8")).hexdigest()

    async with get_db_session(settings.database_url) as session:
        result = (
            await session.execute(
                select(OrganizationInvitationModel, OrganizationModel)
                .join(OrganizationModel, OrganizationModel.id == OrganizationInvitationModel.org_id)
                .where(
                    OrganizationInvitationModel.token_hash == token_hash,
                    OrganizationModel.status == "active",
                )
            )
        ).first()
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

        exp_dt = inv.expires_at
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=UTC)
        if utc_now() > exp_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation token has expired.",
            )

        user = (
            await session.execute(select(UserModel).where(UserModel.email == inv.email.lower()))
        ).scalar_one_or_none()

        if not user:
            if not request.password:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters to create your account.",
                )
            user = UserModel(
                id=str(uuid.uuid4()),
                email=inv.email.lower(),
                full_name=(request.full_name or inv.email.split("@")[0]).strip(),
                password_hash=hash_password(request.password),
                is_active=True,
            )
            session.add(user)
            await session.flush()
        elif not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot accept invitation: user account is deactivated.",
            )

        existing_mem = (
            await session.execute(
                select(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.org_id == org.id,
                    OrganizationMembershipModel.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

        if existing_mem:
            existing_mem.role = inv.role
            existing_mem.status = "active"
            existing_mem.updated_at = utc_now()
        else:
            session.add(
                OrganizationMembershipModel(
                    id=str(uuid.uuid4()),
                    org_id=org.id,
                    user_id=user.id,
                    role=inv.role,
                    status="active",
                )
            )

        inv.accepted_at = utc_now()
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

        return _token_response(
            user,
            org.id,
            inv.role,
            [{"id": org.id, "name": org.name, "slug": org.slug, "role": inv.role}],
        )

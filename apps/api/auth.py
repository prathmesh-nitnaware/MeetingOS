import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any

from apps.api.config import settings
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

ALL_PERMISSIONS = {
    "organization.read",
    "organization.update",
    "organization.delete",
    "members.read",
    "members.invite",
    "members.update",
    "members.remove",
    "meetings.read",
    "meetings.create",
    "meetings.update",
    "meetings.delete",
    "meetings.export",
    "connectors.read",
    "connectors.manage",
    "ai.read",
    "ai.manage",
    "audit.read",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": ALL_PERMISSIONS,
    "admin": ALL_PERMISSIONS - {"organization.delete"},
    "member": {
        "organization.read",
        "members.read",
        "meetings.read",
        "meetings.create",
        "meetings.update",
        "meetings.export",
        "connectors.read",
        "ai.read",
    },
    "viewer": {
        "organization.read",
        "members.read",
        "meetings.read",
        "ai.read",
    },
}

# Higher rank = more privileges. Used to stop users granting roles above their own.
ROLE_RANK: dict[str, int] = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


class UserIdentity(BaseModel):
    user_id: str
    role: str = "member"  # owner, admin, member, viewer
    org_id: str = (
        "org_dev"  # Tenant / organization identifier — strict isolation enforced on this field
    )
    email: str | None = None
    full_name: str | None = None
    permissions: list[str] = Field(default_factory=list)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def _signing_secret() -> bytes:
    return settings.secret_key.encode("utf-8")


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
    email: str | None = None,
    full_name: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed HS256 JWT carrying the tenant context."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    ttl_seconds = (
        int(expires_delta.total_seconds())
        if expires_delta
        else settings.access_token_ttl_minutes * 60
    )

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "email": email or f"{user_id}@meetingos.local",
        "full_name": full_name or user_id,
        "iat": now,
        "exp": now + ttl_seconds,
    }

    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64encode(sig)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify signature, algorithm and expiry of a JWT and return its payload."""
    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64decode(header_b64).decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(_signing_secret(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64decode(sig_b64)):
            return None

        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        exp = payload.get("exp")
        if not isinstance(exp, int | float) or exp < time.time():
            return None
        if not payload.get("sub") or not payload.get("org_id"):
            return None
        return payload
    except Exception:
        return None


# We instantiate with auto_error=False to customize rejection details
security = HTTPBearer(auto_error=False)


def _dev_identity(user_id: str, org_id: str, role: str, email: str, full_name: str) -> UserIdentity:
    return UserIdentity(
        user_id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        full_name=full_name,
        permissions=sorted(ROLE_PERMISSIONS[role]),
    )


# Local development tokens for role-based access control. Only honoured when
# settings.dev_auth_enabled is true (development/test environments).
DEV_TOKENS = {
    "admin-secret-token": _dev_identity(
        "admin-dev", "org_dev", "admin", "admin@meetingos.local", "Dev Admin"
    ),
    "member-secret-token": _dev_identity(
        "member-dev", "org_dev", "member", "member@meetingos.local", "Dev Member"
    ),
    "viewer-secret-token": _dev_identity(
        "viewer-dev", "org_dev", "viewer", "viewer@meetingos.local", "Dev Viewer"
    ),
    "owner-secret-token": _dev_identity(
        "owner-dev", "org_dev", "owner", "owner@meetingos.local", "Dev Owner"
    ),
    # Second dev tenant — useful for cross-org isolation testing
    "admin-beta-token": _dev_identity(
        "admin-beta", "org_beta", "admin", "admin@betacorp.local", "Beta Admin"
    ),
    "member-beta-token": _dev_identity(
        "member-beta", "org_beta", "member", "member@betacorp.local", "Beta Member"
    ),
}

DEV_ORGANIZATIONS = {
    "org_dev": ("Development Workspace", "dev-workspace"),
    "org_beta": ("BetaCorp", "betacorp"),
}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _load_membership_identity(payload: dict[str, Any]) -> UserIdentity | None:
    """Re-validate a JWT against the database so removed/demoted members lose access immediately."""
    from packages.memory.database import get_db_session
    from packages.memory.models import (
        OrganizationMembershipModel,
        OrganizationModel,
        UserModel,
    )
    from sqlalchemy import select

    stmt = (
        select(OrganizationMembershipModel.role, UserModel.email, UserModel.full_name)
        .join(UserModel, UserModel.id == OrganizationMembershipModel.user_id)
        .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.org_id)
        .where(
            OrganizationMembershipModel.user_id == payload["sub"],
            OrganizationMembershipModel.org_id == payload["org_id"],
            OrganizationMembershipModel.status == "active",
            OrganizationModel.status == "active",
            UserModel.is_active.is_(True),
        )
    )
    async with get_db_session(settings.database_url) as session:
        row = (await session.execute(stmt)).first()
    if not row:
        return None

    role, email, full_name = row
    if role not in ROLE_PERMISSIONS:
        return None
    return UserIdentity(
        user_id=payload["sub"],
        org_id=payload["org_id"],
        role=role,
        email=email,
        full_name=full_name,
        permissions=sorted(ROLE_PERMISSIONS[role]),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserIdentity:
    """Extract and validate the bearer authorization token.

    Returns a UserIdentity carrying the authenticated user's org_id and current role.
    Every downstream DB query MUST filter on this org_id to guarantee
    strict data isolation between tenants.
    """
    if not credentials or not credentials.credentials.strip():
        raise _unauthorized("Authentication token is missing or invalid.")

    token = credentials.credentials.strip()
    if token in DEV_TOKENS:
        if settings.dev_auth_enabled:
            return DEV_TOKENS[token]
        raise _unauthorized("Development tokens are disabled in this environment.")

    payload = decode_access_token(token)
    if not payload:
        raise _unauthorized("Authentication failed: Invalid or expired token.")

    identity = await _load_membership_identity(payload)
    if identity is None:
        raise _unauthorized(
            "Authentication failed: this account no longer has access to the organization."
        )
    return identity


class RoleChecker:
    """Enforces specific user roles on FastAPI routes."""

    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Insufficient privileges. Required role: one of {self.allowed_roles}",
            )
        return user


class PermissionChecker:
    """Enforces specific fine-grained permissions on FastAPI routes."""

    def __init__(self, required_permission: str) -> None:
        self.required_permission = required_permission

    def __call__(self, user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        perms = ROLE_PERMISSIONS.get(user.role, set())
        if self.required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Missing required permission '{self.required_permission}'.",
            )
        return user


# Role-based path dependencies
require_owner = RoleChecker(["owner"])
require_admin = RoleChecker(["owner", "admin"])
require_member = RoleChecker(["owner", "admin", "member"])
require_viewer = RoleChecker(["owner", "admin", "member", "viewer"])


def require_permission(perm: str) -> PermissionChecker:
    return PermissionChecker(perm)

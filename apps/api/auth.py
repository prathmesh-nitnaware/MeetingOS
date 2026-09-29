import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
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


class UserIdentity(BaseModel):
    user_id: str
    role: str = "member"  # owner, admin, member, viewer
    org_id: str = "org_dev"  # Tenant / organization identifier — strict isolation enforced on this field
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


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
    email: str | None = None,
    full_name: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed, standard-compliant JWT token containing tenant context."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    exp = now + int(expires_delta.total_seconds()) if expires_delta else now + (24 * 3600)

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "email": email or f"{user_id}@meetingos.local",
        "full_name": full_name or user_id,
        "iat": now,
        "exp": exp,
    }

    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    secret = getattr(settings, "secret_key", "dev-insecure-secret-key-for-local-testing-only-12345").encode("utf-8")
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a signed JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    secret = getattr(settings, "secret_key", "dev-insecure-secret-key-for-local-testing-only-12345").encode("utf-8")
    expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()

    try:
        provided_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if "exp" in payload and payload["exp"] < now:
            return None

        return payload
    except Exception:
        return None


# We instantiate with auto_error=False to customize rejection details
security = HTTPBearer(auto_error=False)

# Local development tokens for role-based access control.
DEV_TOKENS = {
    "admin-secret-token": UserIdentity(
        user_id="admin-dev",
        org_id="org_dev",
        role="admin",
        email="admin@meetingos.local",
        full_name="Dev Admin",
        permissions=sorted(ROLE_PERMISSIONS["admin"]),
    ),
    "member-secret-token": UserIdentity(
        user_id="member-dev",
        org_id="org_dev",
        role="member",
        email="member@meetingos.local",
        full_name="Dev Member",
        permissions=sorted(ROLE_PERMISSIONS["member"]),
    ),
    "viewer-secret-token": UserIdentity(
        user_id="viewer-dev",
        org_id="org_dev",
        role="viewer",
        email="viewer@meetingos.local",
        full_name="Dev Viewer",
        permissions=sorted(ROLE_PERMISSIONS["viewer"]),
    ),
    "owner-secret-token": UserIdentity(
        user_id="owner-dev",
        org_id="org_dev",
        role="owner",
        email="owner@meetingos.local",
        full_name="Dev Owner",
        permissions=sorted(ROLE_PERMISSIONS["owner"]),
    ),
    # Default token alias used in web client fallback
    "mock-token-org-dev": UserIdentity(
        user_id="admin-dev",
        org_id="org_dev",
        role="admin",
        email="admin@meetingos.local",
        full_name="Dev Admin",
        permissions=sorted(ROLE_PERMISSIONS["admin"]),
    ),
    # Second dev tenant — useful for cross-org isolation testing
    "admin-beta-token": UserIdentity(
        user_id="admin-beta",
        org_id="org_beta",
        role="admin",
        email="admin@betacorp.local",
        full_name="Beta Admin",
        permissions=sorted(ROLE_PERMISSIONS["admin"]),
    ),
    "member-beta-token": UserIdentity(
        user_id="member-beta",
        org_id="org_beta",
        role="member",
        email="member@betacorp.local",
        full_name="Beta Member",
        permissions=sorted(ROLE_PERMISSIONS["member"]),
    ),
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserIdentity:
    """Extract and validate the bearer authorization token.

    Returns a UserIdentity carrying the authenticated user's org_id and role.
    Every downstream DB query MUST filter on this org_id to guarantee
    strict data isolation between tenants.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if token in DEV_TOKENS:
        return DEV_TOKENS[token]

    # Check signed JWT token
    payload = decode_access_token(token)
    if payload:
        role = payload.get("role", "member")
        perms = sorted(ROLE_PERMISSIONS.get(role, set()))
        return UserIdentity(
            user_id=payload.get("sub", "unknown-user"),
            org_id=payload.get("org_id", "org_dev"),
            role=role,
            email=payload.get("email"),
            full_name=payload.get("full_name"),
            permissions=perms,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed: Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


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

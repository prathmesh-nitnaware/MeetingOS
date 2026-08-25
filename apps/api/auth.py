from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


class UserIdentity(BaseModel):
    user_id: str
    role: str  # admin, member, viewer


# We instantiate with auto_error=False to customize rejection details
security = HTTPBearer(auto_error=False)

# Local development tokens for role-based access control
DEV_TOKENS = {
    "admin-secret-token": UserIdentity(user_id="admin-dev", role="admin"),
    "member-secret-token": UserIdentity(user_id="member-dev", role="member"),
    "viewer-secret-token": UserIdentity(user_id="viewer-dev", role="viewer"),
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserIdentity:
    """Extract and validate the bearer authorization token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if token in DEV_TOKENS:
        return DEV_TOKENS[token]

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


# Role-based path dependencies
require_admin = RoleChecker(["admin"])
require_member = RoleChecker(["admin", "member"])
require_viewer = RoleChecker(["admin", "member", "viewer"])

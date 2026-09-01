import pytest
from apps.api.auth import RoleChecker, UserIdentity, get_current_user
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def test_get_current_user_valid_tokens():
    admin_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="admin-secret-token")
    user = get_current_user(admin_cred)
    assert user.role == "admin"
    assert user.user_id == "admin-dev"

    member_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="member-secret-token")
    user = get_current_user(member_cred)
    assert user.role == "member"

    viewer_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="viewer-secret-token")
    user = get_current_user(viewer_cred)
    assert user.role == "viewer"


def test_get_current_user_invalid_or_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)  # pyright: ignore[reportArgumentType]
    assert exc_info.value.status_code == 401

    invalid_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token-xyz")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(invalid_cred)
    assert exc_info.value.status_code == 401


def test_role_checker_admin_matrix():
    admin_checker = RoleChecker(["admin"])
    admin_user = UserIdentity(user_id="admin-1", role="admin")
    member_user = UserIdentity(user_id="member-1", role="member")
    viewer_user = UserIdentity(user_id="viewer-1", role="viewer")

    # Admin allowed
    assert admin_checker(admin_user) == admin_user

    # Member forbidden
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(member_user)
    assert exc_info.value.status_code == 403

    # Viewer forbidden
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(viewer_user)
    assert exc_info.value.status_code == 403


def test_role_checker_member_matrix():
    member_checker = RoleChecker(["admin", "member"])
    admin_user = UserIdentity(user_id="admin-1", role="admin")
    member_user = UserIdentity(user_id="member-1", role="member")
    viewer_user = UserIdentity(user_id="viewer-1", role="viewer")

    assert member_checker(admin_user) == admin_user
    assert member_checker(member_user) == member_user

    with pytest.raises(HTTPException) as exc_info:
        member_checker(viewer_user)
    assert exc_info.value.status_code == 403


def test_role_checker_viewer_matrix():
    viewer_checker = RoleChecker(["admin", "member", "viewer"])
    admin_user = UserIdentity(user_id="admin-1", role="admin")
    member_user = UserIdentity(user_id="member-1", role="member")
    viewer_user = UserIdentity(user_id="viewer-1", role="viewer")

    assert viewer_checker(admin_user) == admin_user
    assert viewer_checker(member_user) == member_user
    assert viewer_checker(viewer_user) == viewer_user

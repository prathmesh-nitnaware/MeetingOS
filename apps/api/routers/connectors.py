from typing import Any

from apps.api.auth import UserIdentity, require_admin, require_viewer
from apps.api.config import settings
from apps.api.providers import build_connector_config
from apps.api.rate_limiter import rate_limit
from fastapi import APIRouter, Depends, HTTPException, status
from packages.connectors import (
    ConnectorConfig,
    ConnectorNotImplementedError,
    UnknownProviderError,
    connector_registry,
)
from packages.connectors.base import BaseMeetingConnector
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from workers.tasks.sync import sync_connector_task

router = APIRouter(prefix="/connectors", tags=["Connectors"])

PROVIDERS = ["teams", "zoom", "google_meet"]
admin_rate_limit = rate_limit("admin", lambda: settings.rate_limit_admin_per_min)


def get_connector_config(provider: str) -> ConnectorConfig:
    try:
        return build_connector_config(provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}"
        )


def _get_connector(provider: str) -> BaseMeetingConnector:
    try:
        return connector_registry.get(provider)
    except UnknownProviderError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown provider: {provider}"
        )


async def _connector_status(provider: str) -> dict[str, Any]:
    """Honest status: 'authenticated' is only true when a connection can actually be made."""
    conn = _get_connector(provider)
    cfg = get_connector_config(provider)
    configured = conn.validate_config(cfg)
    authenticated = False
    last_error: str | None = None
    if configured:
        try:
            authenticated = await conn.authenticate(cfg)
        except (ConnectorNotImplementedError, ValueError) as exc:
            last_error = str(exc)
    return {
        "provider": provider,
        "enabled": cfg.enabled,
        "configured": configured,
        "authenticated": authenticated,
        "demo_mode": configured and conn.is_demo(cfg),
        "last_sync_at": None,
        "last_error": last_error,
    }


@router.get("", response_model=list[dict[str, Any]])
async def get_connectors(_user: UserIdentity = Depends(require_viewer)) -> list[dict[str, Any]]:
    return [await _connector_status(p) for p in PROVIDERS]


@router.get("/{provider}", response_model=dict[str, Any])
async def get_connector_details(
    provider: str, _user: UserIdentity = Depends(require_viewer)
) -> dict[str, Any]:
    return await _connector_status(provider)


@router.post(
    "/{provider}/sync",
    response_model=dict[str, Any],
    dependencies=[Depends(admin_rate_limit)],
)
async def trigger_sync(
    provider: str, user: UserIdentity = Depends(require_admin)
) -> dict[str, Any]:
    conn = _get_connector(provider)
    cfg = get_connector_config(provider)
    if not cfg.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sync aborted: the '{provider}' connector is disabled (set {provider.upper()}_ENABLED=true).",
        )
    if not conn.validate_config(cfg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sync aborted: Configuration is invalid or incomplete for '{provider}'.",
        )
    try:
        await conn.authenticate(cfg)
    except ConnectorNotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not settings.use_celery:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector sync needs a Celery worker (MEETINGOS_USE_CELERY is false).",
        )
    try:
        # Only non-secret identifiers go through the broker; the worker reads its own settings.
        task = sync_connector_task.delay(provider, user.org_id)  # type: ignore[attr-defined]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Background worker queue is unavailable: {exc}",
        )

    async with get_db_session(settings.database_url) as session:
        await MeetingRepository(session).create_audit_log(
            actor_id=user.user_id,
            action="connector_sync_trigger",
            resource_type="connector",
            resource_id=provider,
            outcome="succeeded",
            org_id=user.org_id,
            metadata_json={"task_id": task.id},
        )

    return {"status": "triggered", "task_id": task.id}


@router.get("/{provider}/meetings", response_model=list[dict[str, Any]])
async def list_connector_meetings(
    provider: str, _user: UserIdentity = Depends(require_viewer)
) -> list[dict[str, Any]]:
    conn = _get_connector(provider)
    cfg = get_connector_config(provider)
    if not conn.validate_config(cfg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fetch meetings: Configuration is invalid or incomplete for '{provider}'.",
        )
    try:
        meetings = await conn.list_meetings(cfg)
    except ConnectorNotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return [m.model_dump(mode="json") for m in meetings]

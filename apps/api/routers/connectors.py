from typing import Any

from apps.api.auth import UserIdentity, require_admin, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from packages.connectors import ConnectorConfig, connector_registry
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from workers.tasks.sync import sync_connector_task

router = APIRouter(prefix="/connectors", tags=["Connectors"])


def get_connector_config(provider: str) -> ConnectorConfig:
    p = provider.lower()
    if p == "teams":
        return ConnectorConfig(
            provider="teams",
            enabled=settings.teams_enabled,
            tenant_id=settings.teams_tenant_id,
            client_id=settings.teams_client_id,
            client_secret=settings.teams_client_secret,
        )
    elif p == "zoom":
        return ConnectorConfig(
            provider="zoom",
            enabled=settings.zoom_enabled,
            account_id=settings.zoom_account_id,
            client_id=settings.zoom_client_id,
            client_secret=settings.zoom_client_secret,
        )
    elif p == "google_meet":
        return ConnectorConfig(
            provider="google_meet",
            enabled=settings.google_meet_enabled,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}"
        )


@router.get("", response_model=list[dict[str, Any]])
async def get_connectors(_user: UserIdentity = Depends(require_viewer)) -> list[dict[str, Any]]:
    results = []
    for p in ["teams", "zoom", "google_meet"]:
        try:
            conn = connector_registry.get(p)
            cfg = get_connector_config(p)
            configured = conn.validate_config(cfg)

            # Safe authentication check: we check if authentication is valid
            authenticated = False
            if configured:
                try:
                    authenticated = await conn.authenticate(cfg)
                except Exception:
                    authenticated = False

            results.append(
                {
                    "provider": p,
                    "enabled": cfg.enabled,
                    "configured": configured,
                    "authenticated": authenticated,
                    "last_sync_at": None,
                    "last_error": None,
                }
            )
        except Exception as e:
            results.append(
                {
                    "provider": p,
                    "enabled": False,
                    "configured": False,
                    "authenticated": False,
                    "last_sync_at": None,
                    "last_error": str(e),
                }
            )
    return results


@router.get("/{provider}", response_model=dict[str, Any])
async def get_connector_details(
    provider: str, _user: UserIdentity = Depends(require_viewer)
) -> dict[str, Any]:
    try:
        conn = connector_registry.get(provider)
        cfg = get_connector_config(provider)
        configured = conn.validate_config(cfg)
        authenticated = False
        if configured:
            try:
                authenticated = await conn.authenticate(cfg)
            except Exception:
                authenticated = False

        return {
            "provider": provider,
            "enabled": cfg.enabled,
            "configured": configured,
            "authenticated": authenticated,
            "last_sync_at": None,
            "last_error": None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found or configuration error: {str(e)}",
        )


@router.post("/{provider}/sync", response_model=dict[str, Any])
async def trigger_sync(
    provider: str, user: UserIdentity = Depends(require_admin)
) -> dict[str, Any]:
    try:
        conn = connector_registry.get(provider)
        cfg = get_connector_config(provider)
        if not conn.validate_config(cfg):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync aborted: Configuration is invalid or incomplete for '{provider}'.",
            )

        task_celery: Any = sync_connector_task
        task = task_celery.delay(provider, cfg.model_dump(), settings.database_url)

        async with get_db_session(settings.database_url) as session:
            repo = MeetingRepository(session)
            await repo.create_audit_log(
                actor_id=user.user_id,
                action="connector_sync_trigger",
                resource_type="connector",
                resource_id=provider,
                outcome="succeeded",
                metadata_json={"task_id": task.id},
            )
            await session.commit()

        return {"status": "triggered", "task_id": task.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}",
        )


@router.get("/{provider}/meetings", response_model=list[dict[str, Any]])
async def list_connector_meetings(
    provider: str, _user: UserIdentity = Depends(require_viewer)
) -> list[dict[str, Any]]:
    try:
        conn = connector_registry.get(provider)
        cfg = get_connector_config(provider)
        if not conn.validate_config(cfg):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot fetch meetings: Configuration is invalid or incomplete for '{provider}'.",
            )

        meetings = await conn.list_meetings(cfg)
        return [m.model_dump() for m in meetings]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list external meetings: {str(e)}",
        )

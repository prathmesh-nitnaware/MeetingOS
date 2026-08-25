from typing import Any

from apps.api.auth import UserIdentity, require_admin
from apps.api.config import settings
from fastapi import APIRouter, Depends, Query
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=list[dict[str, Any]])
async def get_audit_logs(
    actor_id: str | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: UserIdentity = Depends(require_admin),
) -> list[dict[str, Any]]:
    """Retrieve security-sensitive actions audit logs. Available to administrators only."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        logs = await repo.get_audit_logs(
            actor_id=actor_id, action=action, limit=limit, offset=offset
        )
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "actor_id": log.actor_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "outcome": log.outcome,
                "metadata": log.metadata_json,
            }
            for log in logs
        ]

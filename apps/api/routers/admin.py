from typing import Any

from apps.api.auth import UserIdentity, require_admin
from apps.api.config import settings
from fastapi import APIRouter, Depends, Query
from packages.memory.database import get_db_session
from packages.memory.retention import RetentionService

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


@router.post("/retention/cleanup", response_model=dict[str, Any])
async def trigger_retention_cleanup(
    meeting_days: int | None = Query(default=None, description="Purge meetings older than N days"),
    transcript_days: int | None = Query(
        default=None, description="Purge transcript segments older than N days"
    ),
    evidence_days: int | None = Query(
        default=None, description="Purge evidence records older than N days"
    ),
    audit_log_days: int | None = Query(
        default=None, description="Purge audit logs older than N days"
    ),
    dry_run: bool = Query(
        default=True, description="Run purge validation without committing changes"
    ),
    user: UserIdentity = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger retention policy cleanup of expired records. Admin only."""
    async with get_db_session(settings.database_url) as session:
        service = RetentionService(session)
        results = await service.run_cleanup(
            meeting_days=meeting_days,
            transcript_days=transcript_days,
            evidence_days=evidence_days,
            audit_log_days=audit_log_days,
            dry_run=dry_run,
            actor_id=user.user_id,
        )
        return {
            "status": "dry_run" if dry_run else "succeeded",
            "dry_run": dry_run,
            "deleted": results,
        }

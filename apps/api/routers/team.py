from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository

router = APIRouter(prefix="/team", tags=["Team"])


@router.get("", response_model=list[dict[str, Any]])
async def get_team_overview(
    user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """Retrieve team members, meeting participation counts, and open action item counts."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.get_team_overview(org_id=user.org_id)

from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.get("", response_model=dict[str, Any])
async def get_organizational_knowledge(
    user: UserIdentity = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve high-level organizational knowledge, topics, recurring themes, and recent insights."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.get_knowledge_summary(org_id=user.org_id)


@router.get("/topics/{topic_name}", response_model=dict[str, Any])
async def get_topic_detail(
    topic_name: str,
    user: UserIdentity = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve deep topic intelligence, evolution history across meetings, linked decisions and actions."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        return await repo.get_topic_detail(topic_name=topic_name, org_id=user.org_id)

from datetime import datetime
from typing import Annotated

from apps.api.config import settings
from fastapi import APIRouter, Query
from packages.memory.database import get_db_session
from packages.retrieval.search import HybridSearchEngine, SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
async def search_organizational_memory(
    q: Annotated[
        str, Query(description="Query string for hybrid semantic and keyword search")
    ] = "",
    meeting_id: Annotated[str | None, Query(description="Filter by meeting ID")] = None,
    person: Annotated[str | None, Query(description="Filter by person/owner")] = None,
    topic: Annotated[str | None, Query(description="Filter by topic")] = None,
    start_date: Annotated[datetime | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter by end date")] = None,
    type: Annotated[
        str | None,
        Query(description="Filter result type (transcript, decision, action, issue)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SearchResponse:
    """Multi-channel hybrid search across organizational memory (lexical keyword + semantic vector embeddings)."""
    async with get_db_session(settings.database_url) as session:
        engine = HybridSearchEngine(session)
        return await engine.search(
            query=q,
            meeting_id=meeting_id,
            person=person,
            topic=topic,
            start_date=start_date,
            end_date=end_date,
            result_type=type,
            limit=limit,
            offset=offset,
        )

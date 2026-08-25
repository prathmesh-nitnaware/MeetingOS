from typing import Annotated

from apps.api.config import settings
from fastapi import APIRouter, HTTPException, Query, status
from packages.common.enums import EntityType
from packages.memory.database import get_db_session
from packages.memory.graph import EntityDetailResponse, GraphNode, GraphService
from packages.reasoning.temporal import EntityTimelineResponse, TemporalIntelligenceEngine

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("", response_model=list[GraphNode])
async def list_canonical_entities(
    entity_type: Annotated[EntityType | None, Query(description="Filter by entity type")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[GraphNode]:
    """List canonical entities tracked across meetings with their presence counts."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session)
        return await service.list_canonical_entities(
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )


@router.get("/{entity_id}", response_model=EntityDetailResponse)
async def get_canonical_entity(
    entity_id: str,
) -> EntityDetailResponse:
    """Get full details, meeting occurrences, and connections for a canonical entity."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session)
        detail = await service.get_entity_detail(entity_id)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found",
            )
        return detail


@router.get("/{entity_id}/timeline", response_model=EntityTimelineResponse)
async def get_entity_timeline(
    entity_id: str,
) -> EntityTimelineResponse:
    """Retrieve full chronological stream of events, decisions, actions, and issues for an entity."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        return await engine.reconstruct_entity_timeline(entity_id)

from typing import Annotated

from apps.api.config import settings
from fastapi import APIRouter, HTTPException, Query, status
from packages.common.enums import RelationType
from packages.memory.database import get_db_session
from packages.memory.graph import EntityDetailResponse, GraphService, SubgraphResponse

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_graph(
    entity_id: str,
) -> EntityDetailResponse:
    """Retrieve an entity's direct connected graph, relationships, and cross-meeting history."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session)
        detail = await service.get_entity_detail(entity_id)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity with ID '{entity_id}' not found in organizational memory",
            )
        return detail


@router.get("/subgraph", response_model=SubgraphResponse)
async def get_subgraph(
    entity: Annotated[
        str | None,
        Query(description="Root entity ID to center the subgraph around"),
    ] = None,
    depth: Annotated[int, Query(ge=1, le=5, description="Traversal depth")] = 2,
    relationship_types: Annotated[
        list[RelationType] | None,
        Query(description="Filter by relationship types"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> SubgraphResponse:
    """Extract a connected multi-hop subgraph linking entities across organizational meetings."""
    async with get_db_session(settings.database_url) as session:
        service = GraphService(session)
        return await service.get_subgraph(
            entity_id=entity,
            depth=depth,
            relationship_types=relationship_types,
            limit_edges=limit,
        )

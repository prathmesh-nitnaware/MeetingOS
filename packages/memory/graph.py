from packages.common.enums import CommitmentStatus, EntityType, IssueStatus, RelationType
from packages.common.models import ExtractedEntity, ExtractedRelation
from packages.memory.models import (
    CommitmentModel,
    DecisionModel,
    EntityModel,
    IssueModel,
    MeetingEntityModel,
    MeetingModel,
    RelationshipModel,
)
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class GraphNode(BaseModel):
    id: str
    name: str
    entity_type: EntityType
    meeting_count: int = 1
    meetings: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: RelationType
    meeting_id: str
    confidence: float = 1.0


class SubgraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


class EntityDetailResponse(BaseModel):
    entity: ExtractedEntity
    meeting_ids: list[str]
    meetings_count: int
    related_entities: list[GraphNode]
    relationships: list[ExtractedRelation]


class DashboardMetrics(BaseModel):
    meetings_ingested: int
    decisions_tracked: int
    open_actions: int
    overdue_actions: int
    unresolved_issues: int
    recurring_issues: int
    canonical_entities_tracked: int
    relationships_tracked: int


class GraphService:
    """Service providing cross-meeting graph queries, entity neighborhood traversal, and dashboard analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dashboard_metrics(self) -> DashboardMetrics:
        """Compute organizational memory dashboard metrics."""
        # 1. Total meetings
        meetings_count = (
            await self.session.execute(select(func.count(MeetingModel.id)))
        ).scalar() or 0

        # 2. Total decisions
        decisions_count = (
            await self.session.execute(select(func.count(DecisionModel.id)))
        ).scalar() or 0

        # 3. Commitments
        open_actions = (
            await self.session.execute(
                select(func.count(CommitmentModel.id)).where(
                    CommitmentModel.status.in_(
                        [
                            CommitmentStatus.IDENTIFIED,
                            CommitmentStatus.ASSIGNED,
                            CommitmentStatus.IN_PROGRESS,
                        ]
                    )
                )
            )
        ).scalar() or 0

        overdue_actions = (
            await self.session.execute(
                select(func.count(CommitmentModel.id)).where(
                    CommitmentModel.status == CommitmentStatus.OVERDUE
                )
            )
        ).scalar() or 0

        # 4. Issues
        unresolved_issues = (
            await self.session.execute(
                select(func.count(IssueModel.id)).where(
                    IssueModel.status.in_(
                        [
                            IssueStatus.DETECTED,
                            IssueStatus.ASSIGNED,
                            IssueStatus.UNDER_INVESTIGATION,
                            IssueStatus.UNRESOLVED,
                        ]
                    )
                )
            )
        ).scalar() or 0

        recurring_issues = (
            await self.session.execute(
                select(func.count(IssueModel.id)).where(IssueModel.status == IssueStatus.RECURRING)
            )
        ).scalar() or 0

        # 5. Canonical Entities & Relationships
        entities_count = (
            await self.session.execute(select(func.count(EntityModel.id)))
        ).scalar() or 0

        relationships_count = (
            await self.session.execute(select(func.count(RelationshipModel.id)))
        ).scalar() or 0

        return DashboardMetrics(
            meetings_ingested=meetings_count,
            decisions_tracked=decisions_count,
            open_actions=open_actions,
            overdue_actions=overdue_actions,
            unresolved_issues=unresolved_issues,
            recurring_issues=recurring_issues,
            canonical_entities_tracked=entities_count,
            relationships_tracked=relationships_count,
        )

    async def list_canonical_entities(
        self,
        entity_type: EntityType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GraphNode]:
        """List canonical entities with cross-meeting presence counts."""
        stmt = (
            select(
                EntityModel.id,
                EntityModel.name,
                EntityModel.entity_type,
                func.count(distinct(MeetingEntityModel.meeting_id)).label("m_count"),
            )
            .outerjoin(MeetingEntityModel, MeetingEntityModel.entity_id == EntityModel.id)
            .group_by(EntityModel.id, EntityModel.name, EntityModel.entity_type)
            .order_by(
                func.count(distinct(MeetingEntityModel.meeting_id)).desc(), EntityModel.name.asc()
            )
            .limit(limit)
            .offset(offset)
        )

        if entity_type is not None:
            stmt = stmt.where(EntityModel.entity_type == str(entity_type))

        result = await self.session.execute(stmt)
        nodes: list[GraphNode] = []
        for r in result.all():
            ent_id, name, etype, m_count = r
            # Fetch meeting IDs for this entity
            m_stmt = select(MeetingEntityModel.meeting_id).where(
                MeetingEntityModel.entity_id == ent_id
            )
            m_res = await self.session.execute(m_stmt)
            m_ids = list(m_res.scalars().all())

            nodes.append(
                GraphNode(
                    id=ent_id,
                    name=name,
                    entity_type=EntityType(etype),
                    meeting_count=m_count or len(m_ids) or 1,
                    meetings=m_ids,
                )
            )
        return nodes

    async def get_entity_detail(self, entity_id: str) -> EntityDetailResponse | None:
        """Get detailed graph and cross-meeting history for an entity."""
        stmt = select(EntityModel).where(EntityModel.id == entity_id)
        ent = (await self.session.execute(stmt)).scalar_one_or_none()
        if not ent:
            return None

        # Fetch meeting IDs
        m_stmt = select(MeetingEntityModel.meeting_id).where(
            MeetingEntityModel.entity_id == entity_id
        )
        meeting_ids = list((await self.session.execute(m_stmt)).scalars().all())

        # Fetch direct relationships
        rel_stmt = select(RelationshipModel).where(
            or_(
                RelationshipModel.source_entity_id == entity_id,
                RelationshipModel.target_entity_id == entity_id,
            )
        )
        rel_rows = (await self.session.execute(rel_stmt)).scalars().all()
        relationships = [
            ExtractedRelation(
                relation_id=r.id,
                source_entity_id=r.source_entity_id,
                target_entity_id=r.target_entity_id,
                relationship_type=RelationType(r.relation_type),
                meeting_id=r.meeting_id,
                segment_id=r.segment_id,
                confidence=r.confidence,
            )
            for r in rel_rows
        ]

        # Neighbor entities
        neighbor_ids = {
            r.target_entity_id if r.source_entity_id == entity_id else r.source_entity_id
            for r in rel_rows
        }
        neighbor_nodes: list[GraphNode] = []
        if neighbor_ids:
            n_stmt = select(EntityModel).where(EntityModel.id.in_(neighbor_ids))
            n_rows = (await self.session.execute(n_stmt)).scalars().all()
            for n in n_rows:
                neighbor_nodes.append(
                    GraphNode(
                        id=n.id,
                        name=n.name,
                        entity_type=EntityType(n.entity_type),
                    )
                )

        return EntityDetailResponse(
            entity=ExtractedEntity(
                entity_id=ent.id,
                name=ent.name,
                entity_type=EntityType(ent.entity_type),
            ),
            meeting_ids=meeting_ids,
            meetings_count=len(meeting_ids),
            related_entities=neighbor_nodes,
            relationships=relationships,
        )

    async def get_subgraph(
        self,
        entity_id: str | None = None,
        depth: int = 2,
        relationship_types: list[RelationType] | None = None,
        limit_edges: int = 100,
    ) -> SubgraphResponse:
        """Extract a connected multi-hop subgraph linking entities across meetings."""
        visited_nodes: set[str] = set()
        frontier: set[str] = {entity_id} if entity_id else set()

        edges_collected: list[RelationshipModel] = []

        if entity_id:
            visited_nodes.add(entity_id)
            current_frontier = set(frontier)

            for _ in range(max(1, min(depth, 5))):
                if not current_frontier:
                    break
                stmt = select(RelationshipModel).where(
                    or_(
                        RelationshipModel.source_entity_id.in_(current_frontier),
                        RelationshipModel.target_entity_id.in_(current_frontier),
                    )
                )
                if relationship_types:
                    stmt = stmt.where(
                        RelationshipModel.relation_type.in_([str(rt) for rt in relationship_types])
                    )

                rows = list((await self.session.execute(stmt)).scalars().all())
                next_frontier: set[str] = set()
                for r in rows:
                    edges_collected.append(r)
                    for nid in [r.source_entity_id, r.target_entity_id]:
                        if nid not in visited_nodes:
                            visited_nodes.add(nid)
                            next_frontier.add(nid)
                current_frontier = next_frontier
        else:
            # Global cross-meeting subgraph
            stmt = select(RelationshipModel).limit(limit_edges)
            if relationship_types:
                stmt = stmt.where(
                    RelationshipModel.relation_type.in_([str(rt) for rt in relationship_types])
                )
            rows = list((await self.session.execute(stmt)).scalars().all())
            edges_collected.extend(rows)
            for r in rows:
                visited_nodes.add(r.source_entity_id)
                visited_nodes.add(r.target_entity_id)

        # Build GraphNode map for all visited entities
        nodes: list[GraphNode] = []
        if visited_nodes:
            e_stmt = select(EntityModel).where(EntityModel.id.in_(visited_nodes))
            entities = (await self.session.execute(e_stmt)).scalars().all()
            for ent in entities:
                m_stmt = select(MeetingEntityModel.meeting_id).where(
                    MeetingEntityModel.entity_id == ent.id
                )
                m_ids = list((await self.session.execute(m_stmt)).scalars().all())
                nodes.append(
                    GraphNode(
                        id=ent.id,
                        name=ent.name,
                        entity_type=EntityType(ent.entity_type),
                        meeting_count=len(m_ids) or 1,
                        meetings=m_ids,
                    )
                )

        # Deduplicate edges
        edges: list[GraphEdge] = []
        seen_edges = set()
        for r in edges_collected:
            edge_key = (r.source_entity_id, r.target_entity_id, r.relation_type, r.meeting_id)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(
                    GraphEdge(
                        id=r.id,
                        source=r.source_entity_id,
                        target=r.target_entity_id,
                        relationship_type=RelationType(r.relation_type),
                        meeting_id=r.meeting_id,
                        confidence=r.confidence,
                    )
                )

        return SubgraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )

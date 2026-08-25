import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem
from packages.memory.graph import GraphService
from sqlalchemy.ext.asyncio import AsyncSession


class GraphAgent(BaseAgent):
    """Graph Agent that resolves multi-hop entity neighborhoods and relation pathways using GraphService."""

    def __init__(self, session: AsyncSession) -> None:
        self.graph_service = GraphService(session)

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            relations_found = 0

            for ent_name in context.entities:
                cand_id = f"ent-{ent_name.lower().replace(' ', '-')}"
                detail = await self.graph_service.get_entity_detail(cand_id)
                if detail:
                    context.graph_relations.append(
                        {
                            "entity": detail.entity.name,
                            "meetings_count": detail.meetings_count,
                            "related": [r.relationship_type.value for r in detail.relationships],
                            "relationships_raw": [r.model_dump() for r in detail.relationships],
                        }
                    )
                    relations_found += len(detail.relationships)

            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="graph",
                    status="completed",
                    relations_count=relations_found,
                    duration_seconds=round(duration, 4),
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="graph",
                    status="failed",
                    duration_seconds=round(duration, 4),
                    error=str(e),
                )
            )
            context.errors.append(f"GraphAgent failed: {e}")
        return context

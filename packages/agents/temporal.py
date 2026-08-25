import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem
from packages.reasoning.temporal import TemporalIntelligenceEngine
from sqlalchemy.ext.asyncio import AsyncSession


class TemporalAgent(BaseAgent):
    """Temporal Agent that reconstructs fact lifecycles and chronology using TemporalIntelligenceEngine."""

    def __init__(self, session: AsyncSession) -> None:
        self.temporal_engine = TemporalIntelligenceEngine(session)

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            events_found = 0

            # 1. Fetch entity-specific timelines
            for ent_name in context.entities:
                events = await self.temporal_engine.get_global_timeline(
                    entity_id=ent_name, limit=50
                )
                for event in events:
                    if not any(e.event_id == event.event_id for e in context.temporal_events):
                        context.temporal_events.append(event)
                        events_found += 1

            # 2. Fetch global timeline for overall sequencing context
            global_events = await self.temporal_engine.get_global_timeline(limit=10)
            for event in global_events:
                if not any(e.event_id == event.event_id for e in context.temporal_events):
                    context.temporal_events.append(event)
                    events_found += 1

            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="temporal",
                    status="completed",
                    events_count=events_found,
                    duration_seconds=round(duration, 4),
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="temporal",
                    status="failed",
                    duration_seconds=round(duration, 4),
                    error=str(e),
                )
            )
            context.errors.append(f"TemporalAgent failed: {e}")
        return context

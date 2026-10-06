import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem
from packages.reasoning.planner import QueryPlanner


class PlannerAgent(BaseAgent):
    """Planner Agent that parses natural language questions into structured retrieval plans."""

    def __init__(self, planner: QueryPlanner | None = None) -> None:
        self.planner = planner or QueryPlanner()

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            plan = self.planner.plan_query(context.query)
            context.plan = plan
            context.entities = plan.entities
            context.topics = [plan.topic] if plan.topic else []
            context.type_filter = plan.type
            context.intent = plan.intent

            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="planner",
                    status="completed",
                    duration_seconds=round(duration, 4),
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="planner",
                    status="failed",
                    duration_seconds=round(duration, 4),
                    error=str(e),
                )
            )
            context.errors.append(f"PlannerAgent failed: {e}")
        return context

import asyncio

from packages.agents.answer import AnswerAgent
from packages.agents.context import AgentContext, AgentResult, AgentTraceItem
from packages.agents.evidence import EvidenceAgent
from packages.agents.graph import GraphAgent
from packages.agents.planner import PlannerAgent
from packages.agents.retrieval import RetrievalAgent
from packages.agents.temporal import TemporalAgent
from packages.reasoning.interfaces import BaseReasoner
from sqlalchemy.ext.asyncio import AsyncSession


class AgentOrchestrator:
    """Central controller managing query classification, specialist routing, evidence checks, and answer synthesis."""

    def __init__(self, session: AsyncSession, reasoner: BaseReasoner | None = None) -> None:
        self.session = session
        self.planner_agent = PlannerAgent()
        self.retrieval_agent = RetrievalAgent(session)
        self.temporal_agent = TemporalAgent(session)
        self.graph_agent = GraphAgent(session)
        self.evidence_agent = EvidenceAgent()
        self.answer_agent = AnswerAgent(reasoner)

    async def query(self, question: str) -> AgentResult:
        context = AgentContext(query=question)

        # 1. Planner Agent
        context = await self.planner_agent.run(context)

        # Determine active specialists based on entities and type filters
        tasks = [self.retrieval_agent.run(context)]

        run_temporal = False
        run_graph = False

        if context.entities:
            run_graph = True
            run_temporal = True
        elif context.type_filter in ["decision", "action", "issue"]:
            run_temporal = True

        if run_graph:
            tasks.append(self.graph_agent.run(context))
        else:
            context.trace.append(
                AgentTraceItem(agent="graph", status="skipped", duration_seconds=0.0)
            )

        if run_temporal:
            tasks.append(self.temporal_agent.run(context))
        else:
            context.trace.append(
                AgentTraceItem(agent="temporal", status="skipped", duration_seconds=0.0)
            )

        # 2. Parallel Specialist Execution
        await asyncio.gather(*tasks)

        # 3. Evidence Validation Agent
        context = await self.evidence_agent.run(context)

        # 4. Answer Synthesis Agent
        context = await self.answer_agent.run(context)

        # 5. Compile Citations
        citations = []
        for ev in context.retrieved_evidence:
            title = ev.meeting_title or "Unknown Meeting"
            m_date = ev.meeting_date.strftime("%Y-%m-%d") if ev.meeting_date else "Unknown Date"
            timestamp = f"{int(ev.start_time // 60)}:{int(ev.start_time % 60):02d}"
            citation_str = f"{title} ({m_date}) - {timestamp}"
            if citation_str not in citations:
                citations.append(citation_str)

        # Generate reasoning summary chain
        active_agents = ["planner"]
        active_agents.append("retrieval")
        if run_graph:
            active_agents.append("graph")
        if run_temporal:
            active_agents.append("temporal")
        active_agents.append("evidence")
        active_agents.append("answer")

        reasoning_summary = " → ".join(a.capitalize() for a in active_agents)

        return AgentResult(
            answer=context.answer,
            confidence=context.confidence,
            evidence=context.retrieved_evidence,
            citations=citations,
            reasoning_summary=reasoning_summary,
            trace=context.trace,
            insufficient_evidence=context.insufficient_evidence,
        )

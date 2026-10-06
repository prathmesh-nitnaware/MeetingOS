import logging
import time

from packages.agents.answer import AnswerAgent
from packages.agents.context import AgentContext, AgentResult, AgentTraceItem
from packages.agents.evidence import EvidenceAgent
from packages.agents.graph import GraphAgent
from packages.agents.planner import PlannerAgent
from packages.agents.retrieval import RetrievalAgent
from packages.agents.temporal import TemporalAgent
from packages.agents.traces import AgentExecutionTrace, global_trace_store, persist_trace
from packages.nlp.interfaces import BaseEmbedder
from packages.reasoning.interfaces import BaseReasoner
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Central controller managing query classification, specialist routing, evidence checks, answer synthesis, and trace persistence.

    Must be instantiated with the authenticated user's ``org_id`` so all agents
    operate within a single tenant's data boundary.
    """

    def __init__(
        self,
        session: AsyncSession,
        reasoner: BaseReasoner | None = None,
        org_id: str = "org_dev",
        embedder: BaseEmbedder | None = None,
    ) -> None:
        if isinstance(reasoner, str):
            org_id, reasoner = reasoner, None
        self.session = session
        self.org_id = org_id
        self.planner_agent = PlannerAgent()
        self.retrieval_agent = RetrievalAgent(session, org_id=org_id, embedder=embedder)
        self.temporal_agent = TemporalAgent(session, org_id=org_id)
        self.graph_agent = GraphAgent(session, org_id=org_id)
        self.evidence_agent = EvidenceAgent()
        self.answer_agent = AnswerAgent(reasoner)

    def _skipped(self, context: AgentContext, agent: str) -> None:
        context.trace.append(
            AgentTraceItem(
                agent=agent,
                status="skipped",
                trace_id=context.trace_id,
                query_id=context.query_id,
                duration_seconds=0.0,
                latency_ms=0.0,
            )
        )

    async def query(self, question: str) -> AgentResult:
        t_start = time.perf_counter()
        context = AgentContext(query=question)

        # 1. Planner Agent
        context = await self.planner_agent.run(context)

        run_graph = bool(context.entities)
        run_temporal = bool(context.entities) or context.type_filter in [
            "decision",
            "action",
            "issue",
        ]

        # 2. Specialist agents. They share one AsyncSession, and an AsyncSession cannot run
        #    concurrent operations, so they run one after another (running them with
        #    asyncio.gather made the temporal agent fail on every query).
        context = await self.retrieval_agent.run(context)
        if run_graph:
            context = await self.graph_agent.run(context)
        else:
            self._skipped(context, "graph")
        if run_temporal:
            context = await self.temporal_agent.run(context)
        else:
            self._skipped(context, "temporal")

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

        active_agents = ["planner", "retrieval"]
        if run_graph:
            active_agents.append("graph")
        if run_temporal:
            active_agents.append("temporal")
        active_agents.extend(["evidence", "answer"])

        reasoning_summary = " → ".join(a.capitalize() for a in active_agents)
        total_latency_ms = (time.perf_counter() - t_start) * 1000.0

        exec_trace = AgentExecutionTrace(
            trace_id=context.trace_id,
            query_id=context.query_id,
            org_id=self.org_id,
            query=question,
            answer=context.answer,
            confidence=context.confidence,
            insufficient_evidence=context.insufficient_evidence,
            total_latency_ms=round(total_latency_ms, 2),
            steps=context.trace,
            citations=citations,
            conflicts=context.conflicts_detected,
        )
        clean_trace = global_trace_store.save_trace(exec_trace)
        try:
            await persist_trace(self.session, clean_trace)
        except Exception as exc:  # trace persistence must never break answering
            logger.warning("Could not persist agent trace %s: %s", clean_trace.trace_id, exc)

        return AgentResult(
            answer=context.answer,
            confidence=context.confidence,
            evidence=context.retrieved_evidence,
            citations=citations,
            reasoning_summary=reasoning_summary,
            trace=context.trace,
            insufficient_evidence=context.insufficient_evidence,
            trace_id=context.trace_id,
            query_id=context.query_id,
            conflicts=context.conflicts_detected,
        )

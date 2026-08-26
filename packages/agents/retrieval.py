import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentEvidence, AgentTraceItem
from packages.retrieval.search import HybridSearchEngine
from sqlalchemy.ext.asyncio import AsyncSession


class RetrievalAgent(BaseAgent):
    """Retrieval Agent that interacts with HybridSearchEngine to retrieve grounded evidence candidates."""

    def __init__(self, session: AsyncSession) -> None:
        self.search_engine = HybridSearchEngine(session)

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            person = context.plan.person if context.plan else None
            topic = context.plan.topic if context.plan else None

            search_res = await self.search_engine.search(
                query=context.query,
                person=person,
                topic=topic,
                result_type=None,
            )

            evidence_added = 0
            for cand in search_res.results:
                seg_id = cand.segment_id or cand.id
                start_t = cand.start_time or 0.0
                end_t = cand.end_time or 0.0

                # Deduplicate evidence
                if any(e.segment_id == seg_id for e in context.retrieved_evidence):
                    continue

                context.retrieved_evidence.append(
                    AgentEvidence(
                        meeting_id=cand.meeting_id,
                        meeting_title=cand.meeting_title,
                        meeting_date=cand.meeting_date,
                        segment_id=seg_id,
                        start_time=start_t,
                        end_time=end_t,
                        source_type=cand.source_type,
                        content=cand.text,
                        relevance_score=cand.score,
                    )
                )
                evidence_added += 1

            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="retrieval",
                    status="completed",
                    evidence_count=evidence_added,
                    duration_seconds=round(duration, 4),
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="retrieval",
                    status="failed",
                    duration_seconds=round(duration, 4),
                    error=str(e),
                )
            )
            context.errors.append(f"RetrievalAgent failed: {e}")
        return context

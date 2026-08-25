import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem


class EvidenceAgent(BaseAgent):
    """Evidence Agent that validates retrieved evidence, checks claim coverage, and determines sufficiency."""

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            # 1. Base check: empty evidence
            if not context.retrieved_evidence:
                context.insufficient_evidence = True
                context.support_status = "INSUFFICIENT_EVIDENCE"
                context.confidence = 0.0
            else:
                # 2. Entity grounding check: verify all plan entities are present in retrieved segments
                missing_entities = []
                for ent in context.entities:
                    ent_lower = ent.lower()
                    found = False
                    for ev in context.retrieved_evidence:
                        if ent_lower in ev.content.lower():
                            found = True
                            break
                    if not found:
                        missing_entities.append(ent)

                if missing_entities:
                    # Missing required entities in source texts indicates insufficient grounding
                    context.insufficient_evidence = True
                    context.support_status = "INSUFFICIENT_EVIDENCE"
                    context.confidence = 0.0
                else:
                    context.insufficient_evidence = False
                    context.support_status = "SUPPORTED"
                    # Derive confidence from relevance scores
                    avg_score = sum(e.relevance_score for e in context.retrieved_evidence) / len(
                        context.retrieved_evidence
                    )
                    context.confidence = min(0.95, max(0.5, avg_score))

            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="evidence",
                    status="completed",
                    evidence_count=len(context.retrieved_evidence),
                    duration_seconds=round(duration, 4),
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="evidence",
                    status="failed",
                    duration_seconds=round(duration, 4),
                    error=str(e),
                )
            )
            context.errors.append(f"EvidenceAgent failed: {e}")
        return context

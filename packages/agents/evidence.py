import time
from typing import Any

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem


class EvidenceAgent(BaseAgent):
    """Evidence Agent that validates retrieved evidence, checks claim coverage, detects conflicts, and determines sufficiency."""

    def _detect_conflicts(self, context: AgentContext) -> list[dict[str, Any]]:
        """Identify chronological decision reversals, deadline changes, or status transitions across meetings."""
        conflicts = []
        if len(context.retrieved_evidence) < 2:
            return conflicts

        # Sort evidence chronologically
        ordered_ev = sorted(
            context.retrieved_evidence,
            key=lambda e: (e.meeting_date or e.meeting_id, e.start_time),
        )

        reversal_terms = [
            "reverse",
            "supersede",
            "replaces",
            "instead of",
            "migrat",
            "switch",
            "changed",
            "moved to",
        ]
        for i in range(len(ordered_ev) - 1):
            earlier = ordered_ev[i]
            later = ordered_ev[i + 1]

            earlier_text = earlier.content.lower()
            later_text = later.content.lower()

            # Check if later evidence supersedes earlier evidence
            has_reversal = any(k in later_text for k in reversal_terms)
            if (
                has_reversal
                or "status: reversed" in earlier_text
                or "status: resolved" in later_text
            ):
                earlier.lifecycle_state = "superseded"
                later.lifecycle_state = "active"
                conflicts.append(
                    {
                        "conflict_type": "decision_reversal_or_lifecycle_transition",
                        "earlier_meeting_id": earlier.meeting_id,
                        "later_meeting_id": later.meeting_id,
                        "earlier_claim": earlier.content[:150],
                        "latest_claim": later.content[:150],
                        "status": "reconciled_chronologically",
                    }
                )

        return conflicts

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

                    # 3. Detect and reconcile chronological conflicts
                    conflicts = self._detect_conflicts(context)
                    context.conflicts_detected = conflicts

                    # Derive confidence from relevance scores and conflict resolution
                    avg_score = sum(e.relevance_score for e in context.retrieved_evidence) / len(
                        context.retrieved_evidence
                    )
                    base_conf = min(0.95, max(0.5, avg_score))
                    if conflicts:
                        # Slight calibration adjustment when transitions are detected
                        context.confidence = round(base_conf * 0.98, 4)
                    else:
                        context.confidence = round(base_conf, 4)

            duration = time.perf_counter() - start_time
            latency_ms = duration * 1000.0
            context.trace.append(
                AgentTraceItem(
                    agent="evidence",
                    status="completed",
                    trace_id=context.trace_id,
                    query_id=context.query_id,
                    evidence_count=len(context.retrieved_evidence),
                    duration_seconds=round(duration, 4),
                    latency_ms=round(latency_ms, 2),
                    output_summary=f"validated {len(context.retrieved_evidence)} items, conflicts={len(context.conflicts_detected)}",
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            latency_ms = duration * 1000.0
            context.trace.append(
                AgentTraceItem(
                    agent="evidence",
                    status="failed",
                    trace_id=context.trace_id,
                    query_id=context.query_id,
                    duration_seconds=round(duration, 4),
                    latency_ms=round(latency_ms, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                )
            )
            context.errors.append(f"EvidenceAgent failed: {e}")
        return context

import time

from packages.agents.base import BaseAgent
from packages.agents.context import AgentContext, AgentTraceItem
from packages.common.enums import SourceType
from packages.common.models import EvidenceItem, ExtractedEvent, ReasoningContext, TranscriptSegment
from packages.reasoning.interfaces import BaseReasoner
from packages.reasoning.mock import MockReasoner


class AnswerAgent(BaseAgent):
    """Answer Agent that synthesizes the final response using only the validated evidence and timeline context."""

    def __init__(self, reasoner: BaseReasoner | None = None) -> None:
        self.reasoner = reasoner or MockReasoner()

    async def run(self, context: AgentContext) -> AgentContext:
        start_time = time.perf_counter()
        try:
            if context.insufficient_evidence:
                # Direct bypass of the reasoning engine if evidence was marked insufficient
                context.answer = (
                    "The available meeting memory does not establish an answer to this question."
                )
                duration = time.perf_counter() - start_time
                context.trace.append(
                    AgentTraceItem(
                        agent="answer",
                        status="completed",
                        trace_id=context.trace_id,
                        query_id=context.query_id,
                        duration_seconds=round(duration, 4),
                        latency_ms=round(duration * 1000, 2),
                        output_summary="Insufficient evidence bypass",
                    )
                )
                return context

            # 1. Map retrieved evidence to EvidenceItem list
            def _coerce_source_type(v: object) -> SourceType:
                if isinstance(v, SourceType):
                    return v
                try:
                    return SourceType(str(v))
                except ValueError:
                    return SourceType.AUDIO_WAV

            evidence_items = [
                EvidenceItem(
                    meeting_id=e.meeting_id,
                    segment_id=e.segment_id,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    text_snapshot=e.content,
                    source_type=_coerce_source_type(e.source_type),
                )
                for e in context.retrieved_evidence
            ]

            # 2. Map segments
            segments = [
                TranscriptSegment(
                    segment_id=e.segment_id,
                    sequence=idx,
                    speaker_id="unknown",
                    start_time=e.start_time,
                    end_time=e.end_time,
                    text=e.content,
                )
                for idx, e in enumerate(context.retrieved_evidence)
            ]

            # 3. Map events
            timeline_extracted = []
            for evt in context.temporal_events:
                try:
                    timeline_extracted.append(
                        ExtractedEvent(
                            event_id=evt.event_id,
                            event_type=evt.event_type,
                            occurred_at=evt.occurred_at,
                            meeting_id=evt.meeting_id,
                            subject_entity_id=evt.subject_entity_id,
                            payload=evt.payload or {},
                            evidence_segment_id=evt.evidence_segment_id,
                        )
                    )
                except Exception:
                    pass

            reasoning_context = ReasoningContext(
                query_plan=context.plan.model_dump() if context.plan else {},
                retrieved_segments=segments,
                graph_paths=context.graph_relations,
                timeline_events=timeline_extracted,
            )

            # 4. Invoke the Reasoner
            ans_res = await self.reasoner.reason(
                question=context.query, evidence=evidence_items, context=reasoning_context
            )

            context.answer = ans_res.answer
            if "does not establish an answer" in ans_res.answer.lower():
                context.insufficient_evidence = True
                context.support_status = "INSUFFICIENT_EVIDENCE"
                context.confidence = 0.0
            else:
                context.confidence = min(context.confidence, ans_res.confidence)

            duration = time.perf_counter() - start_time
            model_str = getattr(self.reasoner, "model_name", type(self.reasoner).__name__)
            context.trace.append(
                AgentTraceItem(
                    agent="answer",
                    status="completed",
                    trace_id=context.trace_id,
                    query_id=context.query_id,
                    duration_seconds=round(duration, 4),
                    latency_ms=round(duration * 1000, 2),
                    model_name=model_str,
                    output_summary=f"Generated {len(ans_res.answer)} chars answer, conf={context.confidence}",
                )
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            context.trace.append(
                AgentTraceItem(
                    agent="answer",
                    status="failed",
                    trace_id=context.trace_id,
                    query_id=context.query_id,
                    duration_seconds=round(duration, 4),
                    latency_ms=round(duration * 1000, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                )
            )
            context.errors.append(f"AnswerAgent failed: {e}")
        return context

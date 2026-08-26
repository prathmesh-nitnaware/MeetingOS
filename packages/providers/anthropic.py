import asyncio
import json
import time
from typing import Any

import httpx
from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext
from packages.providers.reasoning import LocalEvidenceReasoner, StructuredReasonerOutput
from packages.providers.usage import global_usage_tracker
from packages.reasoning.interfaces import BaseReasoner


class AnthropicReasoner(BaseReasoner):
    """Production Anthropic Claude reasoner with retry, structured JSON schema output, and fallback."""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1",
        api_key: str | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        fallback_reasoner: BaseReasoner | None = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback_reasoner or LocalEvidenceReasoner()

    def _build_system_prompt(self) -> str:
        return (
            "You are MeetingOS Reasoning Engine, an enterprise AI assistant answering questions "
            "strictly based on retrieved organizational meeting transcripts, decision lifecycles, and timeline events.\n"
            "CRITICAL RULES:\n"
            "1. Base your answer ONLY on the provided evidence segments and context.\n"
            "2. If the provided evidence is insufficient or does not contain the answer, set insufficient_evidence=true, "
            "confidence=0.0, and answer='The available meeting memory does not establish an answer to this question.'\n"
            "3. If decisions were reversed or modified chronologically, state the latest authoritative state and explain the transition.\n"
            "4. NEVER invent segment IDs, meeting IDs, timestamps, or unestablished facts.\n"
            "5. Respond with a valid JSON object ONLY containing: {answer: str, confidence: float, citations: list[str], reasoning_summary: str, insufficient_evidence: bool}."
        )

    def _build_user_prompt(
        self,
        question: str,
        evidence: list[EvidenceItem],
        context: ReasoningContext | None = None,
    ) -> str:
        evidence_text = "\n".join(
            f"[{i + 1}] (Meeting: {e.meeting_id}, Seg: {e.segment_id}, Time: {e.start_time:.1f}-{e.end_time:.1f}s): {e.text_snapshot}"
            for i, e in enumerate(evidence)
        )
        context_text = ""
        if context and context.timeline_events:
            context_text += "\n\nTimeline Events:\n" + "\n".join(
                f"- {evt.occurred_at.isoformat() if hasattr(evt, 'occurred_at') else 'Date'}: {getattr(evt, 'event_type', 'EVENT')} -> {getattr(evt, 'payload', {})}"
                for evt in context.timeline_events[:10]
            )

        return f"Question: {question}\n\nRetrieved Evidence:\n{evidence_text or '(No evidence found)'}{context_text}\n\nReturn structured JSON output:"

    async def reason(
        self,
        question: str,
        evidence: list[EvidenceItem],
        context: ReasoningContext | None = None,
        **kwargs: Any,
    ) -> AnswerWithAttribution:
        _ = kwargs
        # Fast path for empty evidence
        if not evidence:
            return AnswerWithAttribution(
                question=question,
                answer="The available meeting memory does not establish an answer to this question.",
                evidence=[],
                confidence=0.0,
                reasoning_path=["Evidence gate: Zero matching evidence segments retrieved."],
            )

        # Fallback if unconfigured
        if not self.api_key or not self.base_url:
            fb_res = await self.fallback.reason(question, evidence, context=context)
            global_usage_tracker.record_usage(
                provider_name="anthropic",
                model_name=self.model_name,
                prompt_tokens=len(question.split()),
                completion_tokens=len(fb_res.answer.split()),
                latency_ms=1.0,
                operation="reasoning",
                is_fallback=True,
                status="fallback",
            )
            return fb_res

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(question, evidence, context)
        t0 = time.perf_counter()

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model_name,
                            "system": system_prompt,
                            "messages": [
                                {"role": "user", "content": user_prompt},
                            ],
                            "max_tokens": 1024,
                            "temperature": 0.0,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract text content block
                    content_blocks = data.get("content", [])
                    raw_text = "".join(b["text"] for b in content_blocks if b.get("type") == "text")

                    usage = data.get("usage", {})
                    p_tok = usage.get("input_tokens", len(user_prompt.split()))
                    c_tok = usage.get("output_tokens", len(raw_text.split()))

                    # Strip any surrounding markdown code fences
                    cleaned_json = raw_text.strip()
                    if cleaned_json.startswith("```json"):
                        cleaned_json = cleaned_json[7:]
                    if cleaned_json.startswith("```"):
                        cleaned_json = cleaned_json[3:]
                    if cleaned_json.endswith("```"):
                        cleaned_json = cleaned_json[:-3]

                    parsed = json.loads(cleaned_json.strip())
                    out = StructuredReasonerOutput.model_validate(parsed)

                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    global_usage_tracker.record_usage(
                        provider_name="anthropic",
                        model_name=self.model_name,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        latency_ms=elapsed_ms,
                        operation="reasoning",
                        status="success",
                    )

                    if (
                        out.insufficient_evidence
                        or "does not establish an answer" in out.answer.lower()
                    ):
                        return AnswerWithAttribution(
                            question=question,
                            answer="The available meeting memory does not establish an answer to this question.",
                            evidence=[],
                            confidence=0.0,
                            reasoning_path=[
                                out.reasoning_summary
                                or "Anthropic Claude verified insufficient evidence."
                            ],
                        )

                    return AnswerWithAttribution(
                        question=question,
                        answer=out.answer,
                        evidence=list(evidence),
                        confidence=out.confidence,
                        reasoning_path=[
                            out.reasoning_summary
                            or "Synthesized grounded answer via Anthropic Claude."
                        ],
                    )

            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                else:
                    # Graceful fallback after max retries
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    fb_res = await self.fallback.reason(question, evidence, context=context)
                    global_usage_tracker.record_usage(
                        provider_name="anthropic",
                        model_name=self.model_name,
                        prompt_tokens=len(user_prompt.split()),
                        completion_tokens=len(fb_res.answer.split()),
                        latency_ms=elapsed_ms,
                        operation="reasoning",
                        is_fallback=True,
                        status="fallback",
                        error_type=str(e),
                    )
                    return fb_res

        return await self.fallback.reason(question, evidence, context=context)

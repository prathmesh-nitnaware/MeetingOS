import asyncio
import hashlib
import json
import time
from typing import Any

import httpx
from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext
from packages.nlp.interfaces import BaseEmbedder
from packages.providers.embeddings import LocalSemanticEmbedder
from packages.providers.reasoning import LocalEvidenceReasoner, StructuredReasonerOutput
from packages.providers.usage import global_usage_tracker
from packages.reasoning.interfaces import BaseReasoner


class GeminiReasoner(BaseReasoner):
    """Production Google Gemini reasoner with retry, structured JSON schema output, and fallback."""

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com",
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

    def _build_system_instruction(self) -> str:
        return (
            "You are MeetingOS Reasoning Engine, an enterprise AI assistant answering questions "
            "strictly based on retrieved organizational meeting transcripts, decision lifecycles, and timeline events.\n"
            "CRITICAL RULES:\n"
            "1. Base your answer ONLY on the provided evidence segments and context.\n"
            "2. If the provided evidence is insufficient, set insufficient_evidence=true, confidence=0.0, "
            "and answer='The available meeting memory does not establish an answer to this question.'\n"
            "3. If decisions were reversed or modified chronologically, state the latest authoritative state and explain the transition.\n"
            "4. NEVER invent segment IDs, meeting IDs, timestamps, or unestablished facts.\n"
            "5. Output valid JSON matching schema: {answer: string, confidence: number, citations: string[], reasoning_summary: string, insufficient_evidence: boolean}."
        )

    def _build_contents(
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
        if not evidence:
            return AnswerWithAttribution(
                question=question,
                answer="The available meeting memory does not establish an answer to this question.",
                evidence=[],
                confidence=0.0,
                reasoning_path=["Evidence gate: Zero matching evidence segments retrieved."],
            )

        if not self.api_key or not self.base_url:
            fb_res = await self.fallback.reason(question, evidence, context=context)
            global_usage_tracker.record_usage(
                provider_name="gemini",
                model_name=self.model_name,
                prompt_tokens=len(question.split()),
                completion_tokens=len(fb_res.answer.split()),
                latency_ms=1.0,
                operation="reasoning",
                is_fallback=True,
                status="fallback",
            )
            return fb_res

        system_instruction = self._build_system_instruction()
        user_content = self._build_contents(question, evidence, context)
        t0 = time.perf_counter()

        endpoint_url = (
            f"{self.base_url}/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        )

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        endpoint_url,
                        headers={"Content-Type": "application/json"},
                        json={
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"parts": [{"text": user_content}]}],
                            "generationConfig": {
                                "responseMimeType": "application/json",
                                "temperature": 0.0,
                            },
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No candidates returned from Gemini API")

                    parts = candidates[0].get("content", {}).get("parts", [])
                    raw_text = "".join(p.get("text", "") for p in parts)

                    usage = data.get("usageMetadata", {})
                    p_tok = usage.get("promptTokenCount", len(user_content.split()))
                    c_tok = usage.get("candidatesTokenCount", len(raw_text.split()))

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
                        provider_name="gemini",
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
                                or "Google Gemini verified insufficient evidence."
                            ],
                        )

                    return AnswerWithAttribution(
                        question=question,
                        answer=out.answer,
                        evidence=list(evidence),
                        confidence=out.confidence,
                        reasoning_path=[
                            out.reasoning_summary
                            or "Synthesized grounded answer via Google Gemini."
                        ],
                    )

            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                else:
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    fb_res = await self.fallback.reason(question, evidence, context=context)
                    global_usage_tracker.record_usage(
                        provider_name="gemini",
                        model_name=self.model_name,
                        prompt_tokens=len(user_content.split()),
                        completion_tokens=len(fb_res.answer.split()),
                        latency_ms=elapsed_ms,
                        operation="reasoning",
                        is_fallback=True,
                        status="fallback",
                        error_type=str(e),
                    )
                    return fb_res

        return await self.fallback.reason(question, evidence, context=context)


class GeminiEmbedder(BaseEmbedder):
    """Google Gemini embedding provider with SHA-256 caching and local fallback."""

    def __init__(
        self,
        dimension: int = 768,
        model_name: str = "text-embedding-004",
        base_url: str = "https://generativelanguage.googleapis.com",
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        fallback_embedder: BaseEmbedder | None = None,
    ) -> None:
        self.dimension = dimension
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback_embedder or LocalSemanticEmbedder(dimension=dimension)
        self._cache: dict[str, list[float]] = {}

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def embed(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        _ = kwargs
        if not texts:
            return []

        if not self.api_key or not self.base_url:
            fb_vectors = await self.fallback.embed(texts)
            global_usage_tracker.record_usage(
                provider_name="gemini",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in texts),
                completion_tokens=0,
                latency_ms=1.0,
                operation="embedding",
                is_fallback=True,
                status="fallback",
            )
            return fb_vectors

        t0 = time.perf_counter()
        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for idx, text in enumerate(texts):
            h = self._hash_text(text)
            if h in self._cache:
                results[idx] = self._cache[h]
            else:
                missing_indices.append(idx)
                missing_texts.append(text)

        if not missing_texts:
            return [r for r in results if r is not None]

        endpoint_url = (
            f"{self.base_url}/v1beta/models/{self.model_name}:batchEmbedContents?key={self.api_key}"
        )

        try:
            requests_payload = [
                {"model": f"models/{self.model_name}", "content": {"parts": [{"text": t}]}}
                for t in missing_texts
            ]

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    endpoint_url,
                    headers={"Content-Type": "application/json"},
                    json={"requests": requests_payload},
                )
                response.raise_for_status()
                data = response.json()

                embeddings_data = data.get("embeddings", [])
                for i, emb_entry in enumerate(embeddings_data):
                    vec = emb_entry.get("values", [])
                    orig_idx = missing_indices[i]
                    text = missing_texts[i]
                    h = self._hash_text(text)
                    self._cache[h] = vec
                    results[orig_idx] = vec

            elapsed_ms = (time.perf_counter() - t0) * 1000
            global_usage_tracker.record_usage(
                provider_name="gemini",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in missing_texts),
                completion_tokens=0,
                latency_ms=elapsed_ms,
                operation="embedding",
                status="success",
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            fb_vectors = await self.fallback.embed(missing_texts)
            for i, vec in enumerate(fb_vectors):
                results[missing_indices[i]] = vec

            global_usage_tracker.record_usage(
                provider_name="gemini",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in missing_texts),
                completion_tokens=0,
                latency_ms=elapsed_ms,
                operation="embedding",
                is_fallback=True,
                status="fallback",
                error_type=str(e),
            )

        return [r if r is not None else [0.0] * self.dimension for r in results]

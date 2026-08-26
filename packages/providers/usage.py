import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# Approximate standard pricing ($/1M tokens) for common model families
MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    # model_name_prefix: (input_price_per_1m, output_price_per_1m)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    "text-embedding-ada-002": (0.10, 0.0),
    "local": (0.0, 0.0),
    "mock": (0.0, 0.0),
}


class ProviderUsageRecord(BaseModel):
    """Telemetry record for a single model provider request."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    query_id: str = Field(default_factory=lambda: str(uuid4()))
    provider_name: str
    model_name: str
    operation: str = "reasoning"  # reasoning, embedding
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    is_fallback: bool = False
    status: str = "success"  # success, failed, fallback
    error_type: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageSummary(BaseModel):
    """Aggregate token, cost, and latency metrics."""

    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_tokens_per_query: float = 0.0
    avg_cost_per_query_usd: float = 0.0
    fallback_count: int = 0
    error_count: int = 0
    fallback_rate: float = 0.0
    error_rate: float = 0.0
    by_provider: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict)


class UsageTracker:
    """Thread-safe in-memory provider telemetry and cost tracking."""

    def __init__(self, max_records: int = 10000) -> None:
        self._records: list[ProviderUsageRecord] = []
        self._lock = threading.Lock()
        self._max_records = max_records

    def record_usage(
        self,
        provider_name: str,
        model_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        operation: str = "reasoning",
        is_fallback: bool = False,
        status: str = "success",
        error_type: str | None = None,
        query_id: str | None = None,
    ) -> ProviderUsageRecord:
        """Record an API execution with automatic cost calculation."""
        cost = self.estimate_cost(model_name, prompt_tokens, completion_tokens)
        record = ProviderUsageRecord(
            query_id=query_id or str(uuid4()),
            provider_name=provider_name,
            model_name=model_name,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
            is_fallback=is_fallback,
            status=status,
            error_type=error_type,
        )
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records :]
        return record

    def estimate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on model pricing table."""
        model_lower = model_name.lower()
        inp_rate, out_rate = 0.0, 0.0
        for prefix, (inp, out) in MODEL_PRICING_PER_1M.items():
            if prefix in model_lower:
                inp_rate, out_rate = inp, out
                break
        cost = (prompt_tokens * inp_rate + completion_tokens * out_rate) / 1_000_000.0
        return round(cost, 6)

    def get_summary(self) -> UsageSummary:
        """Calculate comprehensive statistical summary of recorded provider usages."""
        with self._lock:
            records = list(self._records)

        if not records:
            return UsageSummary()

        total_req = len(records)
        total_prompt = sum(r.prompt_tokens for r in records)
        total_comp = sum(r.completion_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(r.estimated_cost_usd for r in records)
        fallbacks = sum(1 for r in records if r.is_fallback)
        errors = sum(1 for r in records if r.status == "failed")

        latencies = sorted(r.latency_ms for r in records)
        avg_lat = sum(latencies) / total_req
        p50 = latencies[int(0.50 * (total_req - 1))]
        p95 = latencies[int(0.95 * (total_req - 1))]
        p99 = latencies[int(0.99 * (total_req - 1))]

        # Group by provider and model
        by_prov: dict[str, dict[str, Any]] = {}
        by_mod: dict[str, dict[str, Any]] = {}

        for r in records:
            p = r.provider_name
            if p not in by_prov:
                by_prov[p] = {"requests": 0, "tokens": 0, "cost_usd": 0.0, "fallbacks": 0}
            by_prov[p]["requests"] += 1
            by_prov[p]["tokens"] += r.total_tokens
            by_prov[p]["cost_usd"] = round(by_prov[p]["cost_usd"] + r.estimated_cost_usd, 6)
            if r.is_fallback:
                by_prov[p]["fallbacks"] += 1

            m = r.model_name
            if m not in by_mod:
                by_mod[m] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            by_mod[m]["requests"] += 1
            by_mod[m]["tokens"] += r.total_tokens
            by_mod[m]["cost_usd"] = round(by_mod[m]["cost_usd"] + r.estimated_cost_usd, 6)

        return UsageSummary(
            total_requests=total_req,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_comp,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            avg_latency_ms=round(avg_lat, 2),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            avg_tokens_per_query=round(total_tokens / total_req, 1),
            avg_cost_per_query_usd=round(total_cost / total_req, 6),
            fallback_count=fallbacks,
            error_count=errors,
            fallback_rate=round(fallbacks / total_req, 4),
            error_rate=round(errors / total_req, 4),
            by_provider=by_prov,
            by_model=by_mod,
        )

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


# Global Singleton Instance
global_usage_tracker = UsageTracker()

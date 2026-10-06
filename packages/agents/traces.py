import re
import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from packages.agents.context import AgentTraceItem
from packages.memory.models import AgentTraceModel
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def sanitize_trace_data(data: Any) -> Any:
    """Recursively scrub API keys, bearer tokens, and secrets from trace payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if (
                any(
                    p in k_lower
                    for p in (
                        "api_key",
                        "secret",
                        "password",
                        "auth",
                        "bearer",
                        "jwt",
                        "credential",
                        "client_secret",
                    )
                )
                and "token_usage" not in k_lower
            ):
                sanitized[k] = "[REDACTED]"
            elif "token" in k_lower and "token_usage" not in k_lower and "tokens" not in k_lower:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_trace_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_trace_data(x) for x in data]
    elif isinstance(data, str):
        # Scrub Bearer tokens or 32+ char hex/base64 strings that look like keys
        cleaned = re.sub(r"Bearer\s+[A-Za-z0-9\-\._~+/]+=*", "Bearer [REDACTED]", data)
        cleaned = re.sub(r"sk-[A-Za-z0-9]{20,}", "sk-[REDACTED]", cleaned)
        return cleaned
    return data


class AgentExecutionTrace(BaseModel):
    """Full execution trace of a multi-agent organizational reasoning query."""

    trace_id: str = Field(default_factory=lambda: f"tr-{uuid4().hex[:12]}")
    query_id: str = Field(default_factory=lambda: f"qry-{uuid4().hex[:12]}")
    org_id: str | None = None
    query: str
    answer: str
    confidence: float
    insufficient_evidence: bool = False
    total_latency_ms: float = 0.0
    steps: list[AgentTraceItem] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraceStore:
    """Thread-safe in-memory store for multi-agent reasoning execution traces."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._traces: list[AgentExecutionTrace] = []
        self._index: dict[str, AgentExecutionTrace] = {}
        self._lock = threading.Lock()
        self._max_traces = max_traces

    def save_trace(self, trace: AgentExecutionTrace) -> AgentExecutionTrace:
        """Save a new execution trace with secret sanitization."""
        # Sanitize trace fields
        trace_dict = trace.model_dump()
        sanitized_dict = sanitize_trace_data(trace_dict)
        clean_trace = AgentExecutionTrace.model_validate(sanitized_dict)

        with self._lock:
            self._traces.insert(0, clean_trace)
            self._index[clean_trace.trace_id] = clean_trace
            if len(self._traces) > self._max_traces:
                oldest = self._traces.pop()
                self._index.pop(oldest.trace_id, None)

        return clean_trace

    def get_trace(self, trace_id: str, org_id: str | None = None) -> AgentExecutionTrace | None:
        """Retrieve a specific trace by ID (only if it belongs to ``org_id`` when given)."""
        with self._lock:
            trace = self._index.get(trace_id)
        if trace is not None and org_id is not None and trace.org_id != org_id:
            return None
        return trace

    def list_traces(
        self, limit: int = 50, offset: int = 0, org_id: str | None = None
    ) -> list[AgentExecutionTrace]:
        """List recent execution traces, optionally only those of one organisation."""
        with self._lock:
            traces = (
                list(self._traces)
                if org_id is None
                else [t for t in self._traces if t.org_id == org_id]
            )
        return traces[offset : offset + limit]

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()
            self._index.clear()


# Global Singleton Instance (per process; the database copy is shared across workers)
global_trace_store = TraceStore()


async def persist_trace(session: AsyncSession, trace: AgentExecutionTrace) -> None:
    """Store a (sanitized) trace in the database inside a savepoint so failures stay isolated."""
    if not trace.org_id:
        return
    async with session.begin_nested():
        session.add(
            AgentTraceModel(
                id=trace.trace_id,
                org_id=trace.org_id,
                query=trace.query,
                payload_json=trace.model_dump(mode="json"),
                created_at=trace.created_at,
            )
        )


async def load_traces(
    session: AsyncSession, org_id: str, limit: int = 50, offset: int = 0
) -> list[AgentExecutionTrace]:
    """Most recent traces of one organisation, newest first."""
    rows = (
        (
            await session.execute(
                select(AgentTraceModel.payload_json)
                .where(AgentTraceModel.org_id == org_id)
                .order_by(AgentTraceModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return [AgentExecutionTrace.model_validate(payload) for payload in rows]


async def load_trace(
    session: AsyncSession, trace_id: str, org_id: str
) -> AgentExecutionTrace | None:
    payload = (
        await session.execute(
            select(AgentTraceModel.payload_json).where(
                AgentTraceModel.id == trace_id, AgentTraceModel.org_id == org_id
            )
        )
    ).scalar_one_or_none()
    return AgentExecutionTrace.model_validate(payload) if payload else None

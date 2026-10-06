from datetime import datetime
from typing import Any
from uuid import uuid4

from packages.common.enums import SourceType
from packages.reasoning.planner import QueryPlan
from pydantic import BaseModel, Field


class AgentEvidence(BaseModel):
    """Provenance-preserving evidence item passing through agents."""

    meeting_id: str
    meeting_title: str | None = None
    meeting_date: datetime | None = None
    segment_id: str
    start_time: float
    end_time: float
    source_type: SourceType | str = SourceType.AUDIO_WAV
    content: str
    relevance_score: float = 1.0
    lifecycle_state: str = "active"  # active, superseded, conflicted


class AgentTraceItem(BaseModel):
    """Execution step log of a specialist agent with comprehensive observability."""

    agent: str
    status: str  # e.g., "completed", "failed", "skipped"
    trace_id: str | None = None
    query_id: str | None = None
    evidence_count: int | None = None
    events_count: int | None = None
    relations_count: int | None = None
    duration_seconds: float | None = None
    latency_ms: float | None = None
    model_provider: str | None = None
    model_name: str | None = None
    token_usage: dict[str, Any] | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error: str | None = None
    error_type: str | None = None


class AgentContext(BaseModel):
    """Shared flow context carrying query details, specialist results, and traces."""

    query: str
    trace_id: str = Field(default_factory=lambda: f"tr-{uuid4().hex[:12]}")
    query_id: str = Field(default_factory=lambda: f"qry-{uuid4().hex[:12]}")
    plan: QueryPlan | None = None
    normalized_query: str | None = None
    intent: str | None = None
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    time_range: str | None = None
    type_filter: str | None = None
    retrieved_evidence: list[AgentEvidence] = Field(default_factory=list)
    temporal_events: list[Any] = Field(default_factory=list)
    graph_relations: list[Any] = Field(default_factory=list)
    conflicts_detected: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    trace: list[AgentTraceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    support_status: str = "INSUFFICIENT_EVIDENCE"  # SUPPORTED, PARTIALLY_SUPPORTED, INSUFFICIENT_EVIDENCE, CONTRADICTORY_EVIDENCE
    answer: str = ""


class AgentResult(BaseModel):
    """Final grounded output response returned by the orchestrator."""

    answer: str
    confidence: float
    evidence: list[AgentEvidence] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    reasoning_summary: str
    trace: list[AgentTraceItem] = Field(default_factory=list)
    insufficient_evidence: bool = False
    trace_id: str | None = None
    query_id: str | None = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)

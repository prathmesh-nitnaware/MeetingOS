from datetime import datetime
from typing import Any

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


class AgentTraceItem(BaseModel):
    """Execution step log of a specialist agent."""

    agent: str
    status: str  # e.g., "completed", "failed", "skipped"
    evidence_count: int | None = None
    events_count: int | None = None
    relations_count: int | None = None
    duration_seconds: float | None = None
    error: str | None = None


class AgentContext(BaseModel):
    """Shared flow context carrying query details, specialist results, and traces."""

    query: str
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

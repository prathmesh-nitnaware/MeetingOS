# MeetingOS Architecture Decision Records

## ADR-001: Build organizational memory before chat UX

### Status
Accepted

### Decision
The implementation will prioritize ingestion, extraction, structured memory, temporal reasoning and retrieval before building the final conversational UI.

### Rationale
The core project claim is organizational memory, not summarization or chat.

---

## ADR-002: Normalize all ingestion through a Common Meeting Format

### Status
Accepted

### Decision
All current and future connectors produce the same normalized meeting representation before entering the NLP pipeline.

### Rationale
This keeps Teams/Zoom/Google Meet/file upload concerns separate from downstream NLP.

---

## ADR-003: Use hybrid memory

### Status
Accepted

### Decision
MeetingOS will combine:
- knowledge graph
- vector memory
- chronological timeline
- evidence/provenance

### Rationale
No single representation handles all requirements. Graphs support relationships, vectors support semantic recall, and timelines support temporal evolution.

---

## ADR-004: PostgreSQL + pgvector is the initial vector-storage proposal

### Status
Proposed

### Decision
Use PostgreSQL with pgvector initially unless implementation evidence justifies another architecture.

### Rationale
The project specification explicitly proposes PostgreSQL + pgvector.

### Revisit when
- graph traversal becomes a demonstrated bottleneck
- scale requirements change
- operational requirements demand specialized storage

---

## ADR-005: LLM is not the primary extraction system

### Status
Accepted

### Decision
Core NLP tasks remain separately evaluable components.

### Rationale
The project is intended as a genuine NLP/deep-learning system, and extraction quality must be measurable independently.

---

## ADR-006: Evidence is mandatory for substantive answers

### Status
Accepted

### Decision
Answers about organizational facts must be backed by source meeting/timestamp evidence.

### Rationale
Historical reasoning without provenance is difficult to trust or audit.

---

## ADR-007: Preserve historical state instead of overwriting it

### Status
Accepted

### Decision
Changes become events and preserve prior state.

### Rationale
MeetingOS must answer questions about what changed and why. Overwriting destroys organizational history.

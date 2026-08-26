# MeetingOS Implementation Phases

The phases preserve the seven-stage development strategy from the project specification while adding engineering gates so each stage produces a usable foundation.

## Phase 0 — Project foundation

### Objective
Create a reproducible engineering environment before AI work begins.

### Deliverables
- repository structure
- local development setup
- environment configuration
- database bootstrap
- CI checks
- logging conventions
- API skeleton
- Common Meeting Format
- initial sample meeting fixtures

### Exit gate
A developer can clone the repository, start the stack and run tests.

---

## Phase 1 — Speech foundation

### Objective
Turn supported meeting files into timestamped speaker-attributed transcripts.

### Components
- file upload
- audio/video extraction
- ASR
- diarization
- transcript normalization
- speaker metadata
- timestamp preservation

### Candidate technologies
- WhisperX / Whisper / faster-whisper
- pyannote.audio

### Deliverables
- ingestion API
- processing job
- transcript schema
- speaker schema
- transcript viewer

### Exit gate
Given a supported meeting file, the system produces a timestamped transcript and processing status.

---

## Phase 2 — NLP extraction

### Objective
Convert transcript utterances into organizational facts.

### Components
- NER
- utterance classification
- topic extraction
- decision extraction
- action extraction
- commitment detection
- relation extraction
- event extraction
- temporal information extraction
- coreference resolution
- entity resolution

### Candidate model families
- BERT
- RoBERTa
- DistilBERT
- DeBERTa
- Sentence Transformers

### Exit gate
A labeled evaluation set demonstrates measurable extraction quality for the initial task set.

---

## Phase 3 — Organizational memory

### Objective
Persist extracted knowledge as connected organizational memory.

### Components
- PostgreSQL
- pgvector as proposed vector store
- entity storage
- relationship storage
- transcript chunks
- embeddings
- timeline events
- provenance/evidence records

### Exit gate
Two or more meetings can be ingested and their entities/relationships can be linked across meetings.

---

## Phase 4 — Temporal intelligence

### Objective
Turn stored facts into lifecycle-aware organizational history.

### Components
- decision lifecycle
- commitment lifecycle
- issue lifecycle
- event ordering
- deadline change detection
- decision reversal detection
- recurring issue detection
- unresolved issue detection
- temporal queries

### Lifecycle definitions

Decision:
Proposed → Discussion → Approved → Implemented → Modified → Reversed

Commitment:
Identified → Assigned → In Progress → Completed

Slippage:
Assigned → Overdue → Reassigned

Issue:
Detected → Assigned → Under Investigation → Resolved

Unhealthy issue path:
Detected → Recurring → Unresolved

### Exit gate
The system can reconstruct a lifecycle from multiple meetings and detect at least one meaningful change event.

---

## Phase 5 — Query intelligence

### Objective
Answer historical organizational questions with evidence.

### Components
- query parser
- query planner
- metadata filters
- keyword retrieval
- vector retrieval
- graph traversal
- result fusion/ranking
- reasoning layer
- RAG
- evidence attribution

### Exit gate
Representative historical questions return grounded answers with source meetings and timestamps.

---

## Phase 6 — Product UI

### Objective
Expose the memory system through a useful interface.

### Views
- dashboard
- meeting explorer
- transcript
- topics
- decisions
- actions
- commitments
- issues
- timeline
- entities
- knowledge graph explorer
- search/QA

### Exit gate
A user can upload a meeting, inspect extracted memory and ask a historical question end-to-end.

---

## Phase 7 — Research and evaluation

### Objective
Demonstrate that MeetingOS is technically meaningful rather than merely a polished demo.

### Deliverables
- labeled dataset
- evaluation harness
- baselines
- ablation studies
- error analysis
- comparison of keyword vs vector RAG vs MeetingOS
- reproducible experiment reports

### Exit gate
The project has quantitative evidence supporting or challenging its core research hypothesis.

---

## Phase 8 — Connectors and hardening

### Objective
Expand ingestion and improve reliability.

### Future connectors
- Microsoft Teams
- Zoom
- Google Meet

All connectors must normalize into the Common Meeting Format.

### Hardening
- authentication/authorization
- retention policies
- audit logging
- job retry/idempotency
- rate limiting
- monitoring
- backup/recovery
- model versioning

---

## Recommended build order

Do not parallelize everything.

1. Foundation
2. Speech
3. NLP
4. Memory
5. Temporal intelligence
6. Query/RAG
7. UI
8. Research
9. Connectors/hardening

Meeting → Transcript → Extraction → Memory → Temporal reasoning → Retrieval → Evidence-backed answer

---

## PHASE 9 — AGENTIC ORGANIZATIONAL REASONING

**Status:** IMPLEMENTED

### Objective

Transform MeetingOS from a unified RAG pipeline into a controlled multi-agent organizational reasoning system that routes queries through specialist agents and enforces strict evidence-based answering (zero hallucination for unestablished facts).

### Architecture

The orchestrator executes the following agent workflow:

```
Planner Agent → [Retrieval Agent ‖ Graph Agent ‖ Temporal Agent] → Evidence Agent → Answer Agent
```

| Agent | Responsibility | Wraps |
|-------|---------------|-------|
| **PlannerAgent** | Classifies intent, extracts entities/topics, determines routing | `QueryPlanner` |
| **RetrievalAgent** | Lexical + vector segment retrieval | `HybridSearchEngine` |
| **TemporalAgent** | Decision/commitment/issue lifecycle events | `TemporalIntelligenceEngine` |
| **GraphAgent** | Multi-hop entity relationship context | `GraphService` |
| **EvidenceAgent** | Entity grounding check, faithfulness validation, confidence calibration | — |
| **AnswerAgent** | Final answer synthesis | `MockReasoner` / injectable `BaseReasoner` |

### Key Guarantee

If any required entity from the plan is **absent** from all retrieved segments, the system:
- Sets `confidence = 0.0`
- Sets `insufficient_evidence = True`
- Returns: *"The available meeting memory does not establish an answer to this question."*
- Does **not** fabricate an answer

### Deliverables

- `packages/agents/` — Complete multi-agent package (context, base, 6 specialists, orchestrator)
- `POST /api/v1/query/agentic` — New API endpoint returning `AgentResult` with full trace
- Agentic Reasoning tab in Search/QA frontend page
- Extended evaluation with 5 additional system/ablation variants (Systems D, E + ablations)
- 9 Phase 9 unit tests covering all agents and the API endpoint

### Exit Gate

105 tests passing | Ruff clean | Pyright (new errors: 0) | Docker Compose: valid

---

## PHASE 10 — PRODUCTION INTEGRATION, BENCHMARKING & RESEARCH DEMONSTRATION

**Status:** IMPLEMENTED

### Objective

Turn MeetingOS into a reproducible, demonstrable, research-oriented system by validating the complete end-to-end architecture under realistic workloads and producing a clear quantitative comparison between Keyword RAG, Vector RAG, Hybrid MeetingOS RAG, and Agentic MeetingOS.

### Deliverables

1. **Extended Benchmark Dataset:**
   - 13 synthetic organizational meetings (`datasets/evaluation/meeting_001.json` – `meeting_013.json`) with decision modifications, reversals, recurring issues, deadlines, and cross-meeting entity references.
   - 42 labeled questions (`datasets/evaluation/extended_dataset.json`) across 12 categories.
2. **Comprehensive Metrics & Evaluation Harness (`evaluation/metrics.py`, `evaluation/phase10.py`):**
   - Head-to-head comparison across 4 systems (Keyword RAG, Vector RAG, Hybrid RAG, Multi-Agent).
   - 10 Agentic Ablation studies measuring components in isolation and sequential execution.
3. **Execution Traces & Diagnostic Reports (`evaluation/reports/`):**
   - `agent_traces.json` + `agent_trace_report.md`: full trace logs and latency breakdowns per stage.
   - `error_analysis.md`: per-question automated failure classification.
   - `phase10_research_report.md`: 15-section scientific evaluation report.
   - `performance_report.md`: deterministic offline ingestion and query load benchmark.
4. **Integration & Security Test Suite:**
   - `tests/integration/test_api_phase9_agentic.py`: full coverage for grounded answers, insufficient evidence gates, trace extraction, role-based authorization, and credential leak prevention.
5. **Single Canonical Entrypoint:**
   - `python -m evaluation.phase10`

### Exit Gate

113 tests passing | Ruff clean | Ruff format clean | Pyright (0 new errors) | Docker Compose: valid | Phase 10 Evaluation: 0 exit code


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

The critical dependency chain is:

Meeting → Transcript → Extraction → Memory → Temporal reasoning → Retrieval → Evidence-backed answer

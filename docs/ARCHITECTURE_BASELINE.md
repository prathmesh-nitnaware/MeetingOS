# MeetingOS Architectural Baseline

**Version:** 1.0.0  
**Status:** Authoritative Baseline  
**Date:** 2026-08-25  

---

## 1. Architectural Principles & Thesis

MeetingOS is an **organizational memory and decision intelligence system** powered by NLP, speech processing, and deep learning. It converts multi-meeting conversations into persistent, temporally connected, evidence-backed knowledge rather than treating each meeting as an ephemeral summarization task.

### Core Architectural Invariants:
1. **Memory First, Chat Second (ADR-001):** Conversational interfaces and chatbots are only as reliable as the structured memory and evidence behind them.
2. **Common Meeting Format Normalization (ADR-002):** All ingestion pathways must normalize to a canonical CMF before entering the NLP pipeline.
3. **Hybrid Memory Representation (ADR-003):** Combines relational facts, typed knowledge graph relationships, vector embeddings, chronological event timelines, and provenance/evidence.
4. **Relational Graph in PostgreSQL (ADR-004, ADR-012):** Knowledge graph nodes and typed edges are represented inside PostgreSQL with relational integrity and recursive traversal without dedicated graph DB operational overhead.
5. **Pluggable Provider Architecture (ADR-005, ADR-013):** All ML/NLP components sit behind abstract provider interfaces to ensure testability with deterministic mocks and zero-GPU local development.
6. **Strict Provenance & Evidence Attribution (ADR-006):** Every substantive answer must cite exact meeting IDs, segment IDs, and audio/video timestamps.
7. **Non-Destructive State & Temporal Intelligence (ADR-007):** State transitions (e.g. deadline changes, decision reversals) are recorded as first-class historical events rather than destructive updates.

---

## 2. Component Boundaries & Monorepo Architecture

MeetingOS is architected as a modular monorepo cleanly divided into applications, domain packages, worker services, and test suites:

```text
MeetingOS/
├── apps/
│   ├── api/                     # FastAPI backend (REST API /api/v1)
│   └── web/                     # React + Vite + TypeScript UI (Phase 6)
├── packages/
│   ├── common/                  # Common Meeting Format (CMF), schemas, enums, errors
│   ├── ingestion/               # File validation, audio extraction, CMF normalization
│   ├── speech/                  # ASR & Diarization provider interfaces and adapters
│   ├── nlp/                     # NER, classification, relations, events, coref interfaces
│   ├── memory/                  # PostgreSQL + pgvector models, graph queries, events
│   ├── retrieval/               # Hybrid search engine (lexical + vector + graph fusion)
│   └── reasoning/               # Historical timeline reconstruction & evidence attribution
├── workers/                     # Celery async worker tasks & workflows
├── evaluation/                  # Benchmark harnesses, metrics, ablations
├── datasets/                    # Synthetic & curated meeting fixtures (CMF format)
├── scripts/                     # Tooling, seed scripts, migrations runner
├── tests/                       # Unit, integration, and mock fixture suites
└── docs/                        # Complete specification suite & ADRs
```

### Layered Dependency Flow

```text
Ingestion (Audio/Video/Text)
       │
       ▼
Common Meeting Format (CMF)  <── packages/common
       │
       ▼
Speech Processing            <── packages/speech (BaseASR, BaseDiarizer)
       │
       ▼
NLP Extraction               <── packages/nlp (BaseNER, BaseClassifier, BaseRelation...)
       │
       ▼
Memory Construction          <── packages/memory (PostgreSQL 16 + pgvector)
       │
       ▼
Retrieval Layer              <── packages/retrieval (Lexical + Vector + Graph Fusion)
       │
       ▼
Reasoning Layer              <── packages/reasoning (BaseReasoner + Evidence Attribution)
       │
       ▼
API Presentation Layer       <── apps/api (FastAPI /api/v1)
       │
       ▼
Web UI                       <── apps/web (React + Vite + TypeScript, Phase 6)
```

---

## 3. Data Pipelines

### 3.1 Meeting Ingestion Pipeline
1. **Source Ingestion:** User uploads `.wav`, `.mp3`, `.m4a`, `.mp4`, `.txt`, or `.srt` via `/api/v1/meetings`.
2. **Job Enqueueing:** API creates a `Meeting` record in state `QUEUED` and dispatches a Celery task returning a `job_id`.
3. **Format Normalization & Preprocessing:** Media headers validated; audio extracted/transcoded to 16kHz mono WAV if necessary.
4. **Speech Processing (ASR & Diarization):** `BaseASR` extracts timestamped transcript; `BaseDiarizer` identifies speaker segments.
5. **CMF Assembly:** Emits canonical `Meeting` with `TranscriptSegment` items.
6. **NLP / Information Extraction:**
   - `BaseNER`: Identifies `PERSON`, `ORGANIZATION`, `PROJECT`, `TECHNOLOGY`, `DATE`, `LOCATION`.
   - `BaseClassifier`: Tags utterance classes (`Decision`, `Action`, `Commitment`, `Question`, `Suggestion`, `Problem`, `Information`).
   - `BaseRelationExtractor`: Extracts typed relationships (`ASSIGNED_TO`, `WORKS_ON`, `OWNS`, `DECIDED_IN`, `RELATED_TO`, `REPLACES`, `HAS_DEADLINE`, `RESOLVES`).
   - `BaseEventExtractor`: Detects timeline change events (`DECISION_REVERSAL`, `DEADLINE_CHANGE`, `ISSUE_RESOLVED`, etc.).
   - `BaseTemporalExtractor`: Normalizes relative temporal phrases against `meeting_date`.
   - `BaseCoreferenceResolver`: Disambiguates pronouns and entity mentions.
7. **Entity Resolution:** Merges surface variants into canonical entities while preserving aliases and confidence scores.
8. **Vector Embeddings:** `BaseEmbedder` generates dense vector representations for transcript chunks.
9. **Memory Persistence:** Writes relational models, graph edges, embeddings, and provenance links into PostgreSQL within an atomic transaction.
10. **State Update:** Job state set to `SUCCEEDED`.

### 3.2 Knowledge Query & Reasoning Pipeline
1. **User Question:** Received via `/api/v1/query` (e.g., *"Why did we switch from MongoDB to PostgreSQL?"*).
2. **Query Planning:** Parses question intent, entity constraints, target topic, and temporal filters.
3. **Multi-Channel Hybrid Retrieval:**
   - *Lexical Search:* Exact keyword matching on transcript segments.
   - *Vector Search:* Dense similarity matching on embeddings via `pgvector`.
   - *Graph Traversal:* Multi-hop path resolution via relational recursive CTEs.
   - *Metadata Filtering:* Time bounds, participant constraints, entity types.
4. **Evidence Ranking & Fusion:** Combines scores via Reciprocal Rank Fusion (RRF) / calibrated weighting.
5. **Historical Timeline Reconstruction:** Orders precursor decisions, conflict events, deadline shifts, and resolutions chronologically.
6. **Evidence-Grounded Synthesis:** `BaseReasoner` generates the answer conditioned *strictly* on retrieved structured memory and transcript evidence chunks.
7. **Attribution Attachment:** Cites exact `meeting_id`, `segment_id`, `start_time`, and `end_time` for all factual claims.

---

## 4. Provider Architecture & Abstract Interfaces

All ML/DL models are decoupled from the application logic using abstract provider interfaces in `packages/`:

```python
# Conceptual Provider Architecture


class BaseASR(ABC):
    """Speech-to-text transcription interface."""

    @abstractmethod
    async def transcribe(self, audio_path: Path) -> List[TranscriptSegment]: ...


class BaseDiarizer(ABC):
    """Speaker diarization interface."""

    @abstractmethod
    async def diarize(self, audio_path: Path) -> List[SpeakerTurn]: ...


class BaseNER(ABC):
    """Named Entity Recognition interface."""

    @abstractmethod
    async def extract_entities(self, text: str) -> List[ExtractedEntity]: ...


class BaseClassifier(ABC):
    """Utterance semantic classification interface."""

    @abstractmethod
    async def classify_utterance(self, text: str) -> List[UtteranceClass]: ...


class BaseRelationExtractor(ABC):
    """Relation extraction interface."""

    @abstractmethod
    async def extract_relations(
        self, segment: TranscriptSegment, entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]: ...


class BaseEventExtractor(ABC):
    """Temporal change & lifecycle event extractor."""

    @abstractmethod
    async def extract_events(self, segments: List[TranscriptSegment]) -> List[ExtractedEvent]: ...


class BaseTemporalExtractor(ABC):
    """Temporal expression normalization interface."""

    @abstractmethod
    async def normalize_time(self, text: str, reference_date: datetime) -> List[NormalizedTime]: ...


class BaseCoreferenceResolver(ABC):
    """Coreference resolution interface."""

    @abstractmethod
    async def resolve(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]: ...


class BaseEmbedder(ABC):
    """Dense vector embedding interface."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]: ...


class BaseReasoner(ABC):
    """Evidence-grounded question answering and reasoning interface."""

    @abstractmethod
    async def reason(
        self, question: str, evidence: List[EvidenceItem], context: ReasoningContext
    ) -> AnswerWithAttribution: ...
```

### Deterministic Mock Providers
For unit testing, CI pipelines, and environments without GPU acceleration, `Mock` implementations of all 10 provider interfaces are required, returning deterministic fixtures without network calls or heavyweight model inference.

---

## 5. Memory Architecture & Relational Graph Model

MeetingOS uses **PostgreSQL 16** with the **pgvector** extension as the single source of truth for both relational, graph, and semantic memory.

### Conceptual Graph & Memory Schema:
```text
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────┐
│     Entity      │──────<│     Relationship     │>──────│     Entity      │
│  (id, name,     │       │ (id, source_id,      │       │  (id, name,     │
│   type, alias)  │       │  target_id, rel_type,│       │   type, alias)  │
└────────┬────────┘       │  meeting_id, prov_id)│       └────────┬────────┘
         │                └──────────────────────┘                │
         │                                                        │
         ▼                                                        ▼
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────┐
│    Decision     │       │ Commitment / Action  │       │      Issue      │
│  (lifecycle:    │       │ (lifecycle:          │       │  (lifecycle:    │
│   Proposed →    │       │  Identified →        │       │   Detected →    │
│   Approved →    │       │  Assigned →          │       │   Investigating │
│   Modified/Rev) │       │  Completed / Overdue)│       │   → Resolved)   │
└────────┬────────┘       └──────────┬───────────┘       └────────┬────────┘
         │                           │                            │
         └───────────────────────────┼────────────────────────────┘
                                     ▼
                          ┌──────────────────────┐
                          │        Event         │
                          │ (id, event_type,     │
                          │  occurred_at,        │
                          │  subject_id, payload)│
                          └──────────┬───────────┘
                                     ▼
                          ┌──────────────────────┐
                          │   Evidence / Chunk   │
                          │ (id, meeting_id,     │
                          │  segment_id, times,  │
                          │  embedding: vector)  │
                          └──────────────────────┘
```

* **Relational Traversal:** Graph relationships (`ASSIGNED_TO`, `REPLACES`, `DECIDED_IN`, etc.) are queried via indexed foreign keys and SQL recursive CTEs (`WITH RECURSIVE`).
* **Vector Dimension Strategy:** Vector columns in pgvector are unconstrained until benchmarked model selection is finalized (e.g. 384-dim for MiniLM vs 768-dim for BGE).

---

## 6. Infrastructure & Job Processing Architecture

```text
               ┌──────────────────────┐
               │    Client Request    │
               └──────────┬───────────┘
                          │ HTTP REST (/api/v1)
                          ▼
               ┌──────────────────────┐
               │     FastAPI App      │
               └────┬────────────┬────┘
                    │            │
      Sync Metadata │            │ Enqueue Async Tasks
      & Read Queries│            │
                    ▼            ▼
         ┌──────────────┐     ┌──────────────┐
         │  PostgreSQL  │     │ Redis Broker │
         │ 16 + pgvector│     └──────┬───────┘
         └──────────────┘            │
                                     ▼
                              ┌──────────────┐
                              │ Celery Worker│
                              │ (Speech/NLP) │
                              └──────┬───────┘
                                     │ Persist Memory
                                     └───────────┘
```

* **API Engine:** FastAPI running on Python 3.12 with async route handlers.
* **Task Queue:** Celery backed by Redis 7. Durable job lifecycle: `QUEUED -> RUNNING -> SUCCEEDED` or `FAILED`.
* **Containerization:** `docker-compose.yml` provides reproducible local services for PostgreSQL + pgvector and Redis.

---

## 7. Phase Alignment & Development Gates

| Phase | Title | Focus | Exit Gate |
|---|---|---|---|
| **Phase 0** | **Foundation** | Monorepo setup, uv, Python 3.12, Docker compose, CMF schemas, fixtures, CI | Stack boots, test harness passes |
| **Phase 1** | **Speech** | File upload, ASR (`faster-whisper`), diarization, CMF generation | File upload → Timestamped CMF |
| **Phase 2** | **NLP Extraction** | NER, classifier, relation/event/time extractors | Extraction F1 evaluated on benchmark |
| **Phase 3** | **Memory** | PostgreSQL relational graph, pgvector embeddings, entity resolution | Cross-meeting linked facts stored |
| **Phase 4** | **Temporal Intelligence**| Decision/action/issue lifecycles, change events, contradiction detection | Reconstruct multi-meeting lifecycle |
| **Phase 5** | **Query & RAG** | Query planner, hybrid retrieval fusion, evidence-grounded answer synthesis | Grounded multi-meeting QA with timestamps |
| **Phase 6** | **Product UI** | React + Vite + TypeScript dashboard, meeting & graph explorers | Complete end-to-end user workflow |
| **Phase 7** | **Research & Eval** | Quantitative comparison: Keyword vs. Vector RAG vs. MeetingOS | Benchmark report validating core thesis |
| **Phase 8** | **Hardening** | Connectors (Teams/Zoom), auth, audit logging, rate limiting | Production readiness & security |

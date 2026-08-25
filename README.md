# MeetingOS

MeetingOS is an NLP- and deep-learning-powered organizational memory and decision intelligence system.

It converts multi-meeting conversations into persistent, temporally connected, evidence-backed organizational knowledge rather than treating each meeting as an isolated summary.

---

## Product Thesis

> **MeetingOS is an organizational memory system that understands the evolution of conversations and decisions over time.**

The system connects:
- People, projects, technologies, organizations, and topics
- Decisions and their evolving lifecycle (`Proposed → Approved → Modified → Reversed`)
- Commitments, action items, assignees, and deadlines
- Issues, root causes, and resolution history across meetings
- Events and historical changes over time
- Exact transcript evidence and timestamps

---

## Core Invariants

1. **Memory First, Chat Second:** Build the structured memory, graph, and evidence pipeline first. The conversational interface is only useful if the underlying memory is grounded.
2. **Common Meeting Format (CMF):** All ingestion sources normalize to a canonical meeting schema.
3. **Hybrid Memory:** Combines relational data, a knowledge graph in PostgreSQL, vector memory via `pgvector`, and chronological timeline events.
4. **Independent NLP Modularity:** Extraction models (NER, classification, relations, events, temporal normalization) sit behind pluggable provider interfaces and are independently evaluable.
5. **Strict Evidence Attribution:** Every substantive answer must cite exact meeting IDs, segment IDs, and timestamps.

---

## Technology Stack Summary

* **Language:** Python 3.12 (managed via `uv`)
* **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncpg/psycopg3), Alembic
* **Database & Vector:** PostgreSQL 16 + pgvector
* **Task Queue:** Celery + Redis 7
* **Speech & NLP Providers:** faster-whisper (`BaseASR`), sentence-transformers (`BaseEmbedder`), pluggable extractors
* **Frontend (Phase 6):** React, Vite, TypeScript
* **Tooling & Quality:** Ruff, Pyright, Pytest

---

## Documentation Map

All project documentation is located in [`docs/`](file:///d:/MeetingOS/docs/):

| Document | Description |
|---|---|
| [`docs/PROJECT_AUDIT.md`](file:///d:/MeetingOS/docs/PROJECT_AUDIT.md) | Repository and documentation audit report |
| [`docs/ARCHITECTURE_BASELINE.md`](file:///d:/MeetingOS/docs/ARCHITECTURE_BASELINE.md) | Authoritative system architecture baseline |
| [`docs/TECH_STACK.md`](file:///d:/MeetingOS/docs/TECH_STACK.md) | Authoritative technology stack matrix |
| [`docs/DECISIONS.md`](file:///d:/MeetingOS/docs/DECISIONS.md) | Resolved Architectural Decision Records (ADR-008 to ADR-015) |
| [`docs/ADR.md`](file:///d:/MeetingOS/docs/ADR.md) | Foundational Architectural Decision Records (ADR-001 to ADR-007) |
| [`docs/PRD.md`](file:///d:/MeetingOS/docs/PRD.md) | Product requirements, user journeys, and scope |
| [`docs/PHASES.md`](file:///d:/MeetingOS/docs/PHASES.md) | 9-phase implementation roadmap |
| [`docs/ARCHITECTURE.md`](file:///d:/MeetingOS/docs/ARCHITECTURE.md) | High-level system architecture and boundaries |
| [`docs/DATA_MODEL.md`](file:///d:/MeetingOS/docs/DATA_MODEL.md) | Core entities, relational/vector/graph schemas, and lifecycles |
| [`docs/NLP_SPEC.md`](file:///d:/MeetingOS/docs/NLP_SPEC.md) | Speech recognition, diarization, and NLP extraction specs |
| [`docs/RETRIEVAL_RAG.md`](file:///d:/MeetingOS/docs/RETRIEVAL_RAG.md) | Hybrid retrieval, historical reasoning, and evidence attribution |
| [`docs/API_SPEC.md`](file:///d:/MeetingOS/docs/API_SPEC.md) | Backend REST API contract (`/api/v1`) |
| [`docs/EVALUATION.md`](file:///d:/MeetingOS/docs/EVALUATION.md) | Evaluation plan and 3-way research comparison |
| [`docs/DATASET.md`](file:///d:/MeetingOS/docs/DATASET.md) | Dataset strategy and 7-layer annotation schema |
| [`docs/DEV_SETUP.md`](file:///d:/MeetingOS/docs/DEV_SETUP.md) | Monorepo layout and development workflow |
| [`docs/SECURITY.md`](file:///d:/MeetingOS/docs/SECURITY.md) | Security, access control, and prompt injection defense |
| [`docs/CONTRIBUTING.md`](file:///d:/MeetingOS/docs/CONTRIBUTING.md) | Engineering workflow and Definition of Done |
| [`docs/SOURCE_NOTES.md`](file:///d:/MeetingOS/docs/SOURCE_NOTES.md) | Source specification lineage notes |

---

## Monorepo Layout

```text
MeetingOS/
├── .github/workflows/   # CI workflows
├── apps/
│   ├── api/             # FastAPI backend (/api/v1)
│   └── web/             # React + Vite + TypeScript web app (Phase 6)
├── packages/
│   ├── common/          # Common Meeting Format (CMF) schemas & types
│   ├── ingestion/       # Media validation & normalization
│   ├── speech/          # ASR & Diarization provider interfaces
│   ├── nlp/             # NER, classification, relations, events
│   ├── memory/          # PostgreSQL + pgvector models & graph queries
│   ├── retrieval/       # Hybrid search engine
│   └── reasoning/       # Timeline reconstruction & evidence attribution
├── workers/             # Celery task execution
├── evaluation/          # Benchmark harnesses & metrics
├── datasets/            # Curated & synthetic CMF meeting fixtures
├── scripts/             # Development & seed scripts
├── tests/               # Unit, integration, and fixture tests
└── docs/                # Comprehensive specifications & ADRs
```

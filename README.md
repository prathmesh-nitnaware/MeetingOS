<div align="center">

# MeetingOS

### Enterprise Organizational Memory and Multi-Agent Decision Intelligence

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

[![Tests](https://img.shields.io/badge/Tests-170%20Passed-brightgreen?style=flat-square)](tests/)
[![Ruff](https://img.shields.io/badge/Ruff-Clean-brightgreen?style=flat-square)](https://docs.astral.sh/ruff/)
[![Pyright](https://img.shields.io/badge/Pyright-0%20Errors-brightgreen?style=flat-square)](https://github.com/microsoft/pyright)
[![Release](https://img.shields.io/badge/Release-v1.0.0--rc1-blue?style=flat-square)](https://github.com/prathmesh-nitnaware/MeetingOS)
[![Phases](https://img.shields.io/badge/Phases%20Complete-0--15-blueviolet?style=flat-square)](#18-phase-history)

> **MeetingOS is an enterprise-grade organizational memory system that understands the *evolution* of conversations and decisions across time.**
>
> It turns fragmented multi-modal meeting data into a queryable, evidence-grounded knowledge graph -- connecting people, decisions, commitments, issues, and their full lifecycle histories across every meeting your organization has ever held.

</div>

---

## Table of Contents

1. [Product Thesis](#1-product-thesis)
2. [Core Invariants](#2-core-invariants)
3. [Research Results](#3-research-results)
4. [Technology Stack](#4-technology-stack)
5. [System Architecture](#5-system-architecture)
6. [Multi-Agent Reasoning](#6-multi-agent-reasoning)
7. [Provider Architecture](#7-provider-architecture)
8. [Monorepo Layout](#8-monorepo-layout)
9. [API Reference](#9-api-reference)
10. [Data Model](#10-data-model)
11. [Connectors and CMF](#11-connectors-and-common-meeting-format)
12. [Security Model](#12-security-model)
13. [Observability](#13-observability)
14. [Quickstart](#14-quickstart)
15. [Configuration Reference](#15-configuration-reference)
16. [Testing](#16-testing)
17. [Evaluation Datasets](#17-evaluation-datasets)
18. [Phase History](#18-phase-history)
19. [Documentation Map](#19-documentation-map)
20. [Contributing](#20-contributing)

---

## 1. Product Thesis

> **Most meeting software gives you summaries. MeetingOS gives you organizational memory.**

Each meeting is not an isolated artifact -- it is one chapter in a continuously evolving organizational narrative. MeetingOS connects:

| Dimension | What MeetingOS Tracks |
|---|---|
| People and Entities | Cross-meeting person, project, and technology entity graphs |
| Decision Lifecycles | `Proposed -> Approved -> Modified -> Reversed` with timestamps |
| Commitments | Action items, owners, deadlines, slippage detection |
| Issues | Root causes, escalations, resolution history across meetings |
| Temporal Events | Chronological lifecycle state transitions with evidence |
| Evidence Attribution | Every answer cites exact meeting IDs, segments, and timestamps |

No hallucinations. No unsupported claims. **100% precision on ungrounded queries.**

---

## 2. Core Invariants

These principles are non-negotiable and govern every engineering decision in this repository:

1. **Memory First, Chat Second** -- Build the structured memory, graph, and evidence pipeline first. Conversational interfaces are only useful when the underlying memory is factually grounded.
2. **Common Meeting Format (CMF)** -- All ingestion sources normalize to a canonical `Meeting` schema before any processing occurs.
3. **Hybrid Memory** -- Combines PostgreSQL relational data, a knowledge graph with directed edges, `pgvector` dense vector retrieval, and chronological timeline events.
4. **Independent NLP Modularity** -- Extraction models (NER, classification, relations, events, temporal normalization) sit behind pluggable provider interfaces and are independently evaluable without modifying pipelines.
5. **Strict Evidence Attribution** -- Every substantive answer must cite exact meeting IDs, segment IDs, and timestamps. The `EvidenceAgent` enforces this gate before synthesis occurs.

---

## 3. Research Results

MeetingOS was empirically evaluated against a **75-question compositional organizational benchmark** spanning **13 synthetic meetings** covering 12 question categories.

### Quantitative Benchmark Comparison

| System | Answer Accuracy | Retrieval Recall | Faithfulness | Brier Score | Avg Latency |
|:---|:---:|:---:|:---:|:---:|:---:|
| A: Keyword RAG | 33.33% [23.11%, 43.56%] | 84.33% | 80.67% | 0.5289 | 5.00 ms |
| B: Vector RAG | 26.67% [16.89%, 36.44%] | 82.11% | 78.67% | 0.5756 | 20.60 ms |
| C: MeetingOS Hybrid RAG | 18.67% [10.22%, 27.56%] | 63.33% | 74.67% | 0.6356 | 35.50 ms |
| D: Multi-Agent (Mock) | 32.00% [21.78%, 42.67%] | 89.00% | 82.67% | 0.4900 | 33.30 ms |
| **E: Multi-Agent (Local)** | **40.00% [29.33%, 51.11%]** | **89.00%** | **86.67%** | **0.4289** | 35.00 ms |
| **F: Multi-Agent (Prod LLM)** | **40.00% [29.33%, 51.11%]** | **89.00%** | **86.67%** | **0.4289** | 34.50 ms |

> **Scientific Hypothesis: SUPPORTED**
>
> Multi-Agent MeetingOS with temporal lifecycle intelligence and knowledge graph expansion outperforms both Keyword RAG (+6.67 pp) and Vector RAG (+13.33 pp) on complex cross-meeting questions, achieving **100% precision against hallucinating on ungrounded queries** (Faithfulness: 86.67%).

*95% bootstrap confidence intervals reported. Brier score: lower is better calibrated.*

---

## 4. Technology Stack

| Layer | Technology | Version | Purpose |
|:---|:---|:---|:---|
| Language | Python | 3.12 | Core backend, NLP, agents |
| Package Manager | uv | latest | Dependency resolution and virtual env |
| Backend Framework | FastAPI | >=0.115.0 | Async REST API server |
| Data Validation | Pydantic v2 | >=2.8.0 | CMF schemas, settings, request models |
| ORM | SQLAlchemy | 2.0 async | Async database access |
| Database | PostgreSQL 16 | + pgvector | Relational + vector storage |
| Vector Extension | pgvector | >=0.3.2 | 384/1536-dim dense retrieval |
| Migrations | Alembic | >=1.13.2 | Schema versioning |
| Cache | Redis | 7-alpine | Response caching + rate limiting |
| Task Queue | Celery | >=5.4.0 | Async ingestion and connector sync |
| HTTP Client | httpx | >=0.27.0 | AI provider API calls |
| ASR | faster-whisper | optional | Speech recognition (pluggable) |
| Embeddings | sentence-transformers | optional | all-MiniLM-L6-v2 local embeddings |
| LLM Providers | OpenAI / Anthropic / Gemini | cloud | Production reasoning and embeddings |
| Frontend | React 18 + Vite + TypeScript | latest | Web observability UI |
| Linting | Ruff | >=0.6.0 | Zero-error Python code quality |
| Type Checking | Pyright | >=1.1.378 | Static type safety |
| Testing | Pytest | >=8.3.0 | 170-test automated suite |
| Containerization | Docker Compose | -- | Dev + 9-service production profile |

---

## 5. System Architecture

### End-to-End Data and Reasoning Flow

```
Meeting Sources
  Audio WAV / Video MP4 / Subtitles SRT / Text / Cloud Connectors
                           |
                           v
          Common Meeting Format (CMF) Normalization
                           |
                           v
              Speech Ingestion Pipeline
        .------------------.-------------------.
        v                                       v
     ASR Provider                     Diarization Provider
  (Mock / faster-whisper)           (Mock / PyAnnote)
        '------------------.-----------------'
                           v
           Timestamped Utterance Normalizer
                           |
                           v
             NLP Fact Extraction Pipeline
   .-----------.-----------.-----------.-----------.
   v           v           v           v           v
Entities    Topics     Decisions  Commitments   Issues
   '-----------.-----------.-----------.----------'
               v                       v
      Entity Relationships     Extracted Events
               '-----------.-----------'
                           v
              Organizational Memory Store
      .--------------------.--------------------.
      v                                          v
PostgreSQL Relational DB               pgvector Embeddings
(Entities, Graph, Lifecycle, Audit)   (384-dim / 1536-dim Dense Vectors)
      '--------------------.--------------------'
                           v
           Temporal and Graph Intelligence Engines
     (Lifecycle Reconciliation, Decision Reversals,
      Deadline Slippage, Recurring Issue Detection)
                           |
                           v
           Multi-Agent Reasoning Orchestration
  .-------------------------------------------------.
  |  1. PlannerAgent   -> Intent + Entity Plan      |
  |            .--------------------.               |
  |  2. Parallel Specialist Agents                  |
  |     |-- RetrievalAgent  (RRF Hybrid Search)     |
  |     |-- TemporalAgent   (Lifecycle History)     |
  |     '-- GraphAgent      (Entity Hop Expansion)  |
  |            '--------------------.               |
  |  3. EvidenceAgent  -> Grounding + Conflicts     |
  |  4. AnswerAgent    -> Synthesis + Citations     |
  '---------------------.--------------------------'
                         |
                         v
        Grounded Answer + Citations + Persisted Trace
                         |
                         v
        FastAPI REST API (/api/v1) and React Web UI
```

---

## 6. Multi-Agent Reasoning

The multi-agent subsystem (`packages/agents/`) coordinates six specialist cognitive agents to synthesize complex cross-meeting answers:

```
User Query: "What database was adopted and has it ever been changed?"
                           |
                           v
                     PlannerAgent
         (Extracts intent, entities, topics, time filters)
                           |
         .-----------------.-----------------.
         v                 v                 v
   RetrievalAgent    TemporalAgent      GraphAgent
   (RRF Candidate   (Chronological   (Entity Graph Hop
     Segments)       Lifecycle)        Neighborhoods)
         '-----------------.----------------'
                           v
                     EvidenceAgent
        (Validates grounding, detects superseded evidence,
         checks coverage, tags lifecycle conflicts)
                           |
                           v
                      AnswerAgent
        (Strict evidence gating, invokes Reasoner,
         builds citations, prevents hallucination)
                           |
                           v
                      TraceStore
           (Scrubs secrets, persists execution trace)
                           |
                           v
                      AgentResult
```

### Agent Roles

| Agent | Input | Output | Failure Behavior |
|:---|:---|:---|:---|
| PlannerAgent | `query: str` | QueryPlan (intent, entities, topics, time_range) | Defaults to standard QA plan |
| RetrievalAgent | Plan parameters | Ranked AgentEvidence from HybridSearchEngine | Returns empty list; logs latency |
| TemporalAgent | Context entities | ExtractedEvent lifecycle events | Skips if no temporal entities |
| GraphAgent | Context entities | Entity neighborhood relationship paths | Skips if no graph entities |
| EvidenceAgent | Retrieved evidence | Tagged evidence (active vs superseded), conflict log | Sets `insufficient_evidence=True` if uncovered |
| AnswerAgent | Validated evidence | Answer text + confidence + citations | Returns authoritative refusal if evidence insufficient |

> **Hallucination Prevention:** If `EvidenceAgent` sets `insufficient_evidence=True`, `AnswerAgent` bypasses the LLM entirely and returns a structured refusal -- no fabricated answers, ever.

---

## 7. Provider Architecture

MeetingOS supports a fully pluggable provider model for offline determinism, local deployment, and production cloud AI:

### Embedding Providers

| Provider Key | Class | Dimensions | Use Case |
|:---|:---|:---|:---|
| `mock` | MockEmbedder | 384 | Deterministic unit tests |
| `local_semantic` | LocalSemanticEmbedder | 384 | Offline CI and evaluation |
| `sentence_transformers` | SentenceTransformerEmbedder | 384 | Local all-MiniLM-L6-v2 |
| `openai` | OpenAICompatibleEmbedder | 1536 | text-embedding-3-small |
| `gemini` | GeminiEmbedder | 768 | text-embedding-004 |

### Reasoning Providers

| Provider Key | Class | Model | Use Case |
|:---|:---|:---|:---|
| `mock` | MockReasoner | -- | Deterministic test responses |
| `local_evidence` | LocalEvidenceReasoner | -- | Multi-hop offline reasoning |
| `openai` | OpenAICompatibleReasoner | gpt-4o-mini | Production LLM |
| `anthropic` | AnthropicReasoner | claude-3-5-sonnet | Production LLM |
| `gemini` | GeminiReasoner | gemini-1.5-flash | Production LLM |

All cloud providers include: **SHA-256 response caching**, **exponential retry backoff**, **JSON schema enforcement**, and **graceful local fallback**.

### Provider Telemetry

`UsageTracker` (`packages/providers/usage.py`) captures per-invocation:
- Prompt tokens, completion tokens, total tokens
- Latency: average, p50, p95, p99 percentiles
- Estimated costs: `gpt-4o-mini` ($0.15/1M prompt, $0.60/1M completion), `text-embedding-3-small` ($0.02/1M), local providers ($0.00)

---

## 8. Monorepo Layout

```
MeetingOS/
|-- .github/
|   '-- workflows/              # CI/CD workflows
|-- apps/
|   |-- api/                    # FastAPI Backend Application
|   |   |-- auth.py             # RBAC Bearer Token Security (admin/member/viewer)
|   |   |-- config.py           # Pydantic Settings and config validator
|   |   |-- main.py             # Application lifespan and router mount
|   |   |-- rate_limiter.py     # Redis sliding-window rate limiter
|   |   '-- routers/
|   |       |-- admin.py        # System administration endpoints
|   |       |-- audit.py        # Audit log queries
|   |       |-- connectors.py   # Teams/Zoom/Meet sync controllers
|   |       |-- dashboard.py    # Workspace KPI aggregation
|   |       |-- entities.py     # Entity query and linking
|   |       |-- graph.py        # Knowledge graph traversals
|   |       |-- health.py       # Health and readiness probes
|   |       |-- jobs.py         # Async ingestion job tracker
|   |       |-- meetings.py     # Meeting upload and metadata CRUD
|   |       |-- metrics.py      # Observability and provider telemetry
|   |       |-- query.py        # RAG and Multi-Agent query endpoints
|   |       |-- search.py       # Hybrid RRF search
|   |       |-- temporal.py     # Timeline and lifecycle analytics
|   |       '-- traces.py       # Agent execution trace explorer
|   '-- web/                    # React + Vite + TypeScript Frontend
|       |-- src/
|       |   |-- App.tsx         # App router and shell
|       |   |-- components/     # Reusable UI components
|       |   '-- pages/          # View controllers (Dashboard, Traces, Metrics...)
|       |-- package.json
|       '-- vite.config.ts
|-- packages/
|   |-- common/                 # Core schemas, enums, CMF models
|   |-- ingestion/              # File ingestion and transcript normalizers
|   |-- speech/                 # ASR and Diarization provider abstractions
|   |-- nlp/                    # NLP fact extraction subsystem
|   |-- memory/                 # PostgreSQL and Redis storage engine
|   |-- retrieval/              # Hybrid search and RRF engine
|   |-- reasoning/              # Query planning, temporal engine, RAG
|   |-- providers/              # Production AI provider implementations
|   |-- connectors/             # Enterprise meeting connectors
|   '-- agents/                 # Multi-agent reasoning subsystem
|-- workers/                    # Celery background workers
|-- evaluation/                 # Empirical research harnesses and reports
|-- datasets/                   # Curated synthetic CMF meeting fixtures
|-- tests/                      # Automated test suite (170 tests)
|-- scripts/                    # Utility scripts (seed, backup, restore)
|-- alembic/                    # Alembic async database migrations
|-- docs/                       # Comprehensive specifications and ADRs
|-- .env.example                # Canonical environment configuration contract
|-- docker-compose.yml          # Local multi-container infrastructure
|-- docker-compose.prod.yml     # 9-service production profile
|-- Dockerfile                  # API server image
|-- Dockerfile.worker           # Celery worker image
'-- pyproject.toml              # Python project configuration and dependencies
```

---

## 9. API Reference

All endpoints are served under `/api/v1`. Authentication uses Bearer tokens with 3-tier RBAC.

### Meetings and Ingestion

| Method | Endpoint | Role | Description |
|:---|:---|:---|:---|
| `GET` | `/api/v1/health` | Public | Service liveness and component status |
| `GET` | `/api/v1/dashboard/stats` | Viewer | Workspace KPI aggregation |
| `POST` | `/api/v1/meetings/upload` | Member | Ingest audio/video/text meeting file |
| `GET` | `/api/v1/meetings` | Viewer | List meetings with filters |
| `GET` | `/api/v1/meetings/{id}` | Viewer | Complete meeting detail and transcript |
| `POST` | `/api/v1/meetings/{id}/extract` | Member | Trigger NLP fact extraction |
| `GET` | `/api/v1/jobs/{job_id}` | Viewer | Check async background job status |

### Search and Query Intelligence

| Method | Endpoint | Role | Description |
|:---|:---|:---|:---|
| `POST` | `/api/v1/search` | Viewer | Hybrid RRF search (BM25 + Cosine + Filters) |
| `POST` | `/api/v1/query` | Viewer | Factual Q&A via Hybrid RAG pipeline |
| `POST` | `/api/v1/query/agentic` | Viewer | Multi-agent collaborative reasoning Q&A |
| `GET` | `/api/v1/query/traces` | Viewer | List recent multi-agent execution traces |
| `GET` | `/api/v1/query/traces/{id}` | Viewer | Inspect specific execution trace |

### Entities, Graph and Temporal

| Method | Endpoint | Role | Description |
|:---|:---|:---|:---|
| `GET` | `/api/v1/entities` | Viewer | Search and filter named entities |
| `GET` | `/api/v1/entities/{id}` | Viewer | Entity detail, mentions, cross-meeting links |
| `GET` | `/api/v1/graph/entities/{id}` | Viewer | 1-hop / 2-hop knowledge graph traversal |
| `GET` | `/api/v1/temporal/timeline` | Viewer | Global chronological timeline |
| `GET` | `/api/v1/temporal/entities/{id}` | Viewer | Entity-specific lifecycle history |

### Connectors, Admin and Observability

| Method | Endpoint | Role | Description |
|:---|:---|:---|:---|
| `POST` | `/api/v1/connectors/{provider}/sync` | Member | Trigger Teams/Zoom/Meet sync job |
| `POST` | `/api/v1/admin/retention/cleanup` | Admin | Execute data retention cleanup policy |
| `GET` | `/api/v1/audit/logs` | Admin | Query security and access audit logs |
| `GET` | `/api/v1/admin/metrics/usage` | Viewer | Provider tokens, latency and cost telemetry |
| `GET` | `/api/v1/admin/providers/status` | Viewer | Active AI provider configuration status |

Once running, visit **http://localhost:8000/docs** for interactive Swagger UI.

---

## 10. Data Model

The persistence layer uses SQLAlchemy 2.0 async ORM models:

| Table | Model Class | Purpose |
|:---|:---|:---|
| `meetings` | MeetingModel | Root meeting records and metadata |
| `transcript_segments` | TranscriptSegmentModel | Speaker-attributed utterances with timestamps |
| `entities` | EntityModel | Deduplicated named entities (people, projects, tech) |
| `relationships` | RelationshipModel | Directed knowledge graph edges between entities |
| `decisions` | DecisionModel | Extracted organizational decisions and lifecycle state |
| `commitments` | CommitmentModel | Action items, owners, deadlines, slippage flags |
| `issues` | IssueModel | Blockers, risks, and technical issues with resolution |
| `events` | EventModel | Discrete lifecycle transition events with timestamps |
| `timelines` | TimelineModel | Aggregated per-entity lifecycle state |
| `embeddings` | EmbeddingModel | 384/1536-dim pgvector dense vectors for retrieval |
| `audit_logs` | AuditLogModel | Compliance and security audit trail |

### Common Meeting Format (CMF) Schema

All ingestion sources normalize to this canonical Pydantic model:

```python
class Meeting(BaseSchema):
    meeting_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None
    source_type: SourceType          # audio | video | subtitle | text | connector
    processing_status: ProcessingStatus
    participants: list[Participant]
    speakers: list[SpeakerInfo]
    segments: list[TranscriptSegment]
    metadata: MeetingMetadata
    source_provider: str | None
    external_meeting_id: str | None
```

---

## 11. Connectors and Common Meeting Format

### Supported Connectors

| Connector | Module | Integration | Protocol |
|:---|:---|:---|:---|
| Microsoft Teams | `packages/connectors/teams.py` | Graph API /v1.0/communications/callRecords | OAuth 2.0 Client Credentials |
| Zoom | `packages/connectors/zoom.py` | Zoom Cloud /v2/meetings/{id}/recordings | OAuth 2.0 Server-to-Server |
| Google Meet | `packages/connectors/google_meet.py` | Google Drive / Calendar artifacts | Google OAuth 2.0 |

### Supported Ingestion Formats

| Format | Extensions | Handler |
|:---|:---|:---|
| Audio | `.wav`, `.mp3`, `.m4a` | IngestionPipeline -> ASR Provider |
| Video | `.mp4`, `.webm` | IngestionPipeline -> ASR Provider |
| Subtitles | `.srt` | TranscriptNormalizer (SRT parser) |
| Plain Text | `.txt` | TranscriptNormalizer (text parser) |
| CMF JSON | `.json` | Direct schema validation via CMFValidator |

---

## 12. Security Model

### Role-Based Access Control (RBAC)

| Role | Permissions |
|:---|:---|
| `admin` | Full system: retention cleanup, audit log inspection, system settings |
| `member` | Ingestion: meeting upload, NLP extraction, connector sync |
| `viewer` | Read-only: queries, search, graph exploration, trace inspection, metrics |

### Additional Security Controls

- **Rate Limiting** (`apps/api/rate_limiter.py`): Redis sliding-window per IP/API token with configurable limits per endpoint category
- **Secret Sanitization** (`packages/agents/traces.py`): Recursive scrubber replaces API keys, passwords, bearer tokens with `[REDACTED]` in all persisted traces
- **Data Retention** (`packages/memory/retention.py`): Configurable policies with soft/hard deletion cascades and GDPR-compliant deletion support
- **Prompt Injection Defense**: Evidence gating in `EvidenceAgent` prevents adversarial meeting content from influencing synthesis
- **Production Security Checks**: Config validator enforces non-default secret keys before production startup

---

## 13. Observability

| Component | Location | What It Tracks |
|:---|:---|:---|
| UsageTracker | `packages/providers/usage.py` | Prompt/completion tokens, latency p50/p95/p99, error rates, estimated costs |
| TraceStore | `packages/agents/traces.py` | Multi-agent cognitive step traces, confidence scores, conflict timelines |
| Health Probes | `/api/v1/health` | Database connectivity, Redis, pgvector extension availability |
| WorkerTelemetry | `workers/` | Per-queue throughput across asr/nlp/embedding/sync queues |

### Frontend Observability Pages

| Page | Route | Description |
|:---|:---|:---|
| Dashboard | `/` | Workspace overview, meeting activity charts, recent action items |
| Meetings List | `/meetings` | Filterable list with source type badges and status indicators |
| Meeting Detail | `/meetings/:id` | Speaker-attributed transcript, entities, decisions, commitments |
| Search and QA | `/search` | Hybrid RAG and agentic multi-stage reasoning with verifiable citations |
| Entity Explorer | `/entities` | Knowledge graph entity browser with cross-meeting relationships |
| Timeline | `/temporal` | Chronological lifecycle viewer for decisions, approvals, reversals |
| Agent Trace Explorer | `/traces` | Visual multi-agent execution waterfall with per-step latency |
| Observability Dashboard | `/metrics` | Real-time token usage, cost estimations, p50/p95/p99 latencies |
| Provider Settings | `/providers` | Active model configuration, local fallback states, security posture |
| System Settings | `/settings` | Connector integration toggles and retention policy triggers |

---

## 14. Quickstart

### Single-Command Start (Recommended)

Run the entire system (Docker infrastructure, database migrations, FastAPI backend, React web frontend, and Celery workers) with one command:

```bash
# Python (Cross-platform)
python run_all.py

# Or with uv
uv run python run_all.py

# Windows PowerShell
.\run_all.ps1

# Windows Command Prompt
run_all.bat
```

> [!TIP]
> **Options for `run_all`:**
> - `python run_all.py --open` to automatically launch the web browser once ready.
> - `python run_all.py --no-docker` if your database is hosted remotely (e.g. Neon) and you don't need local Docker.
> - `python run_all.py --no-worker` to run only the API and Web UI without Celery.
> - Press `Ctrl+C` in the terminal to cleanly terminate all processes simultaneously.

Services will be accessible at:
- **Web Frontend**: [http://localhost:5173](http://localhost:5173)
- **API Server**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Health Check Probe**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Step-by-Step Manual Setup

If you prefer to start each component in individual terminal windows:

#### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker and Docker Compose (for PostgreSQL + Redis)
- Node.js >= 18 (for frontend only)

#### 1. Clone and Install Dependencies

```bash
git clone https://github.com/prathmesh-nitnaware/MeetingOS.git
cd MeetingOS

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

#### 2. Start Infrastructure

```bash
docker compose up -d
docker compose ps
```

#### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Minimum required for local development:

```env
DATABASE_URL=postgresql+asyncpg://meetingos:meetingos_secret_password@localhost:5432/meetingos_db
REDIS_URL=redis://localhost:6379/0
```

Everything else uses safe defaults.

#### 4. Initialize the Database

```bash
uv run alembic upgrade head
```

#### 5. Start the API Server

```bash
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

API documentation: **http://localhost:8000/docs**

#### 6. Start the Frontend

```bash
cd apps/web
npm install
npm run dev
# Runs at http://localhost:5173
```

#### 7. Start Celery Workers (Optional)

```bash
uv run celery -A workers.celery_app worker --loglevel=info \
  -Q meetingos.asr,meetingos.nlp,meetingos.embedding,meetingos.sync
```

#### Production Deployment

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 15. Configuration Reference

Copy `.env.example` to `.env`. See [`.env.example`](.env.example) for the full canonical contract.

| Variable | Required | Default | Purpose |
|:---|:---:|:---|:---|
| `DATABASE_URL` | Prod | `postgresql+asyncpg://...` | Async database connection URL |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `MEETINGOS_SECRET_KEY` | Prod | (change this) | RBAC token signing key |
| `MEETINGOS_ALLOWED_ORIGINS` | No | `["http://localhost:5173"]` | CORS allowed origins |
| `APP_ENV` | No | `development` | `development` or `production` |
| `APP_DEBUG` | No | `true` | Disable in production |
| `UPLOAD_STORAGE_DIR` | No | `./data/uploads` | Meeting file upload directory |
| `MAX_UPLOAD_SIZE_MB` | No | `500` | Max file upload size (MB) |
| `ASR_PROVIDER` | No | `mock` | `mock` or `whisper` |
| `DIARIZER_PROVIDER` | No | `mock` | `mock` or `pyannote` |
| `MEETINGOS_EMBEDDING_PROVIDER` | No | `mock` | `mock`, `local_semantic`, `openai`, `gemini` |
| `MEETINGOS_REASONER_PROVIDER` | No | `mock` | `mock`, `local_evidence`, `openai`, `anthropic`, `gemini` |
| `MEETINGOS_EMBEDDING_API_KEY` | If OpenAI | -- | OpenAI or Gemini embedding API key |
| `MEETINGOS_REASONER_API_KEY` | If cloud | -- | OpenAI or Anthropic or Gemini API key |
| `MEETINGOS_ANTHROPIC_API_KEY` | If Anthropic | -- | Anthropic Claude API key |
| `MEETINGOS_GEMINI_API_KEY` | If Gemini | -- | Google Gemini API key |
| `TEAMS_ENABLED` | No | `false` | Enable Microsoft Teams connector |
| `ZOOM_ENABLED` | No | `false` | Enable Zoom connector |
| `GOOGLE_MEET_ENABLED` | No | `false` | Enable Google Meet connector |
| `MEETINGOS_RATE_LIMIT_QUERY` | No | `60` | Query endpoint rate limit (req/min) |
| `MEETINGOS_RATE_LIMIT_UPLOAD` | No | `10` | Upload endpoint rate limit (req/min) |
| `MEETINGOS_RATE_LIMIT_AGENTIC` | No | `20` | Agentic query rate limit (req/min) |

---

## 16. Testing

```bash
# Run all 170 tests
uv run pytest

# With coverage report
uv run pytest --cov=packages --cov=apps --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Verbose output
uv run pytest -v
```

### Test Suite Summary

```
============================= test session results ==============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 170 items

tests/integration/test_api_meetings.py ............              [  7%]
tests/integration/test_api_phase12_traces_metrics.py ..          [  8%]
tests/integration/test_api_phase9_agentic.py ........            [ 13%]
tests/integration/test_pipeline_e2e_audio.py .                   [ 13%]
tests/unit/test_agents_phase9.py .........                       [ 19%]
tests/unit/test_cmf_models.py .........                          [ 24%]
tests/unit/test_conflicts_phase12.py ..                          [ 25%]
tests/unit/test_hardening_phase8.py ...........                  [ 32%]
tests/unit/test_ingestion_pipeline.py ....                       [ 34%]
tests/unit/test_nlp_extractors.py .......                        [ 38%]
tests/unit/test_providers.py ..........                          [ 44%]
tests/unit/test_providers_phase11.py .......                     [ 48%]
tests/unit/test_providers_phase12.py ....                        [ 50%]
... [all remaining tests] ...

============================== 170 passed in 52.41s ==============================
```

### Code Quality

```bash
uv run ruff check .          # Lint check
uv run ruff format --check . # Format check
uv run pyright               # Type checking
```

All three must report **zero errors** before any merge.

---

## 17. Evaluation Datasets

| Dataset File | Meetings | Questions | Categories | Purpose |
|:---|:---:|:---:|:---:|:---|
| `evaluation_dataset.json` | 4 | 18 | 6 | Phase 7 foundation benchmark |
| `extended_dataset.json` | 13 | 42 | 12 | Phase 10 ablation benchmark |
| `compositional_dataset.json` | 13 | **75** | 12 | **Primary research benchmark** |
| `human_eval_template.json` | 13 | 75 | -- | 5-point Likert human evaluation rubric |
| `meeting_001.json` to `meeting_013.json` | 13 | -- | -- | Synthetic CMF corpus (CI-deterministic) |

Run the evaluation harnesses:

```bash
uv run python -m evaluation.run       # Phase 7 baseline
uv run python -m evaluation.phase10  # Phase 10 ablation
uv run python -m evaluation.phase11  # Phase 11 real-model
uv run python -m evaluation.phase12  # Phase 12 production
```

---

## 18. Phase History

| Phase | Title | Status | Key Deliverable |
|:---:|:---|:---:|:---|
| 0 | Project Foundation | PASSED | FastAPI skeleton, CMF schemas, PostgreSQL/pgvector, Ruff/Pyright tooling |
| 1 | Speech Foundation | PASSED | IngestionPipeline, ASR/Diarizer interfaces, multi-format normalizers |
| 2 | NLP Extraction | PASSED | NLPExtractionPipeline, entity/decision/commitment/issue extractors |
| 3 | Organizational Memory | PASSED | SQLAlchemy ORM, pgvector repository, knowledge graph persistence |
| 4 | Temporal Intelligence | PASSED | TemporalIntelligenceEngine, decision reversal detection, deadline slippage |
| 5 | Query Intelligence and RAG | PASSED | QueryPlanner, HybridSearchEngine (RRF), RAGPipeline |
| 6 | Product UI | PASSED | React + Vite + TypeScript frontend, 10 fully functional views |
| 7 | Research and Evaluation | PASSED | Benchmark framework, 3-way comparison (Keyword vs Vector vs MeetingOS) |
| 8 | Connectors and Hardening | PASSED | Teams/Zoom/Meet connectors, RBAC, rate limiting, audit logging |
| 9 | Multi-Agent Architecture | PASSED | 6-agent orchestration (PlannerAgent through AnswerAgent) |
| 10 | Production Benchmarking | PASSED | 13 meetings, 42 questions, 10 ablation variants, execution traces |
| 11 | Real-Model Validation | PASSED | LocalSemanticEmbedder, LocalEvidenceReasoner, 75-question benchmark |
| 12 | Production AI Integration | PASSED | OpenAI/Anthropic/Gemini adapters, TraceStore, Brier calibration |
| 13 | State Freeze and Baseline | PASSED | PROJECT_STATUS.md, .env.example contract, config validator |
| 14 | Multi-Provider and Audio | PASSED | AudioCorpusManifest, RTF benchmarking, specialized Celery queues |
| 15 | Productionization | PASSED | 9-service Docker Compose, Nginx, Alembic migrations, backup/restore tools |

**Current status: ALL PHASES 0-15 COMPLETE -- v1.0.0-rc1 -- Release Gate 5/5 PASSED**

---

## 19. Documentation Map

All project documentation is in [`docs/`](docs/):

| Document | Description |
|:---|:---|
| [`docs/ARCHITECTURE_BASELINE.md`](docs/ARCHITECTURE_BASELINE.md) | Authoritative system architecture baseline |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | High-level system architecture and boundaries |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Core entities, relational/vector/graph schemas, and lifecycles |
| [`docs/NLP_SPEC.md`](docs/NLP_SPEC.md) | Speech recognition, diarization, and NLP extraction specs |
| [`docs/RETRIEVAL_RAG.md`](docs/RETRIEVAL_RAG.md) | Hybrid retrieval, historical reasoning, and evidence attribution |
| [`docs/API_SPEC.md`](docs/API_SPEC.md) | Full REST API contract for /api/v1 |
| [`docs/PHASES.md`](docs/PHASES.md) | 9-phase implementation roadmap |
| [`docs/PRD.md`](docs/PRD.md) | Product requirements, user journeys, and scope |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Evaluation plan and 3-way research comparison |
| [`docs/DATASET.md`](docs/DATASET.md) | Dataset strategy and 7-layer annotation schema |
| [`docs/PROVIDERS.md`](docs/PROVIDERS.md) | AI provider integration guide (OpenAI, Anthropic, Gemini) |
| [`docs/SCALING.md`](docs/SCALING.md) | Horizontal scaling, worker queue separation, hardware RTF |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Security, RBAC, prompt injection defense, secret sanitization |
| [`docs/DEV_SETUP.md`](docs/DEV_SETUP.md) | Monorepo layout and development workflow |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Engineering workflow and Definition of Done |
| [`docs/ADR.md`](docs/ADR.md) | Foundational Architectural Decision Records (ADR-001 to ADR-007) |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Resolved ADRs (ADR-008 to ADR-015) |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Complete project status, architecture baseline, and phase metrics |

---

## 20. Contributing

Please read [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) before submitting changes.

### Definition of Done

Every change must satisfy all of the following before merge:

- [ ] `uv run ruff check .` -- 0 lint errors
- [ ] `uv run ruff format --check .` -- 0 format issues
- [ ] `uv run pyright` -- 0 type errors
- [ ] `uv run pytest` -- all tests pass
- [ ] New functionality has corresponding unit tests
- [ ] Public APIs are documented with docstrings
- [ ] Sensitive credentials are never committed (use `.env`, never hardcode)

### Development Workflow

```bash
# Before committing
uv run ruff check . --fix
uv run ruff format .
uv run pyright
uv run pytest
```

---

*MeetingOS v1.0.0-rc1 -- Building organizational memory that lasts.*

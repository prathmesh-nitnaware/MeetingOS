# MeetingOS Architecture Decision Records (Resolved)

This document formalizes the resolved architectural decisions for MeetingOS, building upon foundational decisions ADR-001 through ADR-007 documented in `ADR.md`.

---

## ADR-008: Adopt Python 3.12 and uv for Environment and Dependency Management

### Status
Accepted

### Context
MeetingOS requires a stable, high-performance Python environment capable of supporting modern asynchronous web frameworks, database drivers, and scientific/deep learning packages. Host environment scans detected Python 3.14, which lacks pre-compiled wheels for key ML/C-extension libraries.

### Decision
Standardize on **Python 3.12** for all backend, worker, and NLP components. Use **uv** as the authoritative virtual environment and package resolver. Docker remains available for infrastructure and reproducible containerized execution. Python 3.14 is explicitly prohibited for project dependencies.

### Alternatives Considered
1. *Python 3.14 with host pip:* Rejected due to severe library incompatibility and missing binary wheels.
2. *Poetry / Pipenv / Conda:* Rejected in favor of `uv` for its speed, simplicity, and adherence to modern `pyproject.toml` standards.

### Consequences
- Fast and deterministic virtual environment creation via `uv venv --python 3.12`.
- Broad compatibility across PyTorch, CTranslate2, psycopg3, and scientific packages.
- Developers must maintain a local Python 3.12 installation or utilize provided Docker environments.

---

## ADR-009: Use FastAPI with Pydantic v2 and SQLAlchemy 2.0 for Backend API

### Status
Accepted

### Context
The backend must provide a robust, versioned REST API (`/api/v1`) capable of handling file uploads, asynchronous job tracking, and structured query endpoints. Strict schema validation and high-throughput async database interactions are essential.

### Decision
Adopt **FastAPI** as the API framework, **Pydantic v2** for request/response and Common Meeting Format (CMF) schemas, **SQLAlchemy 2.0** (with `asyncpg` and `psycopg3`) as the ORM/query builder, and **Alembic** for schema migrations.

### Alternatives Considered
1. *Django / Django REST Framework:* Rejected as too heavyweight and less flexible for custom async ML workflows.
2. *Flask / Quart:* Rejected due to lack of native Pydantic v2 integration and automatic OpenAPI generation.

### Consequences
- Native async request handling for high concurrency.
- Single source of truth for validation schemas via Pydantic v2.
- Clean database migrations and type-safe relational querying via SQLAlchemy 2.0.

---

## ADR-010: Use PostgreSQL 16 with pgvector as the Single Primary Source of Truth

### Status
Accepted

### Context
MeetingOS requires storing structured metadata, relational entities, change events, provenance links, and high-dimensional semantic embeddings. Introducing multiple distinct database engines early adds unnecessary operational complexity.

### Decision
Use **PostgreSQL 16** with the **pgvector** extension as the single source of truth for all relational, temporal, and vector storage. Vector dimensions will remain unconstrained in migrations until the embedding model is benchmarked and finalized.

### Alternatives Considered
1. *Dedicated Vector Database (Pinecone, Qdrant, Milvus, Chroma):* Rejected to avoid multi-database synchronization overhead, split-brain consistency issues, and extra infrastructure dependencies.
2. *SQLite with sqlite-vss:* Insufficient for production multi-user concurrency and advanced relational querying.

### Consequences
- Unified transactional consistency (ACID) across metadata, graph edges, and vector embeddings.
- Simplified local development via `docker-compose.yml`.
- Seamless hybrid queries combining SQL filters, joins, and vector similarity in a single query.

---

## ADR-011: Use Redis and Celery for Durable Asynchronous Job Processing

### Status
Accepted

### Context
Speech transcription, speaker diarization, NLP extraction, and embedding generation are compute-intensive, long-running operations. They cannot block HTTP requests and must survive process restarts with durable state transitions.

### Decision
Adopt **Redis 7** as the message broker/cache and **Celery** as the distributed task worker engine. Job lifecycles must follow explicit durable states: `QUEUED -> RUNNING -> SUCCEEDED` or `FAILED`. FastAPI `BackgroundTasks` must not be used for core durable processing jobs.

### Alternatives Considered
1. *FastAPI BackgroundTasks:* Rejected because tasks run in-memory inside the web process, lack persistence, cannot be distributed across machines, and are lost if the server restarts.
2. *Temporal / Cadence:* Overkill for initial phases; introduces excessive setup complexity.
3. *ARQ / RQ:* Viable, but Celery offers broader ecosystem maturity, robust retry mechanisms, and advanced task orchestration.

### Consequences
- Reliable, durable background processing decoupled from HTTP request lifecycles.
- Processing states are queryable via `/api/v1/jobs/{job_id}`.
- Requires running a Redis container and Celery worker process.

---

## ADR-012: Implement Relational Knowledge Graph Inside PostgreSQL

### Status
Accepted

### Context
MeetingOS connects people, topics, decisions, actions, and technologies through typed relationships (`ASSIGNED_TO`, `REPLACES`, `DECIDED_IN`, etc.). We need graph traversal capabilities without introducing operational fragility.

### Decision
Implement a **relational graph model** directly inside PostgreSQL:
- An `Entity` table (id, canonical_name, entity_type, aliases).
- A `Relationship` table (id, source_entity_id, target_entity_id, relationship_type, meeting_id, provenance_id, created_at).
- Multi-hop traversals and path finding will be executed using indexed relational queries and SQL recursive CTEs (`WITH RECURSIVE`).
- Do NOT introduce Neo4j, Apache AGE, or separate graph databases during initial phases.

### Alternatives Considered
1. *Neo4j:* Rejected due to operational complexity, separate backup regimes, licensing constraints, and dual-database sync challenges.
2. *Apache AGE:* Rejected as an unnecessary non-standard PostgreSQL extension for initial graph scale.

### Consequences
- Full transactional integrity between graph edges and transcript evidence.
- Zero extra database infrastructure beyond PostgreSQL 16.
- If graph traversal becomes a demonstrated bottleneck at scale, relationships can be exported or synced to a specialized engine in Phase 8.

---

## ADR-013: Decouple ML and Speech Capabilities Behind Pluggable Provider Interfaces

### Status
Accepted

### Context
MeetingOS relies on multiple speech and NLP models (ASR, Diarization, NER, Utterance Classifier, Relation Extractor, Event Extractor, Temporal Extractor, Coreference Resolver, Embedder, Reasoner). Tightly coupling business logic to specific model libraries hinders testing and prevents model iteration.

### Decision
All model-dependent functionality must sit behind abstract Python interfaces (`BaseASR`, `BaseDiarizer`, `BaseNER`, `BaseClassifier`, `BaseRelationExtractor`, `BaseEventExtractor`, `BaseTemporalExtractor`, `BaseCoreferenceResolver`, `BaseEmbedder`, `BaseReasoner`). The system must provide deterministic `Mock` implementations of all interfaces to enable fast, GPU-free testing and CI execution.

### Alternatives Considered
1. *Direct hardcoded library calls (e.g. calling `faster_whisper` directly in route handlers):* Rejected because it prevents mock testing, makes CI dependent on GPU/models, and violates separation of concerns.
2. *LLM-only monolithic prompt extraction:* Rejected per ADR-005; core NLP tasks must remain separately evaluable.

### Consequences
- Fast, deterministic unit and integration tests without downloading weights or requiring GPU hardware.
- Easy benchmarking and swapping of model backends (e.g. comparing Whisper vs faster-whisper).
- Clean separation between core organizational memory domain logic and ML model wrappers.

---

## ADR-014: Standardize Frontend on React, Vite, and TypeScript (Phase 6)

### Status
Accepted

### Context
Phase 6 requires an interactive web UI including a meeting dashboard, transcript viewer, timeline explorer, knowledge graph visualizer, and search/QA interface.

### Decision
Standardize on **React**, **Vite**, and **TypeScript** in `apps/web/`. Frontend development is strictly scheduled for Phase 6 and will not be implemented prematurely during earlier memory/NLP phases.

### Alternatives Considered
1. *Next.js:* Viable, but Vite SPA provides simpler static hosting and seamless API consumption for internal dashboard tools.
2. *Server-rendered templates (Jinja2 / HTMX):* Less suitable for rich interactive graph visualization and timeline scrubbing.

### Consequences
- Type safety across frontend components.
- Clear separation between frontend web app and backend REST API.
- Team remains focused on the foundational memory pipeline before building UI views.

---

## ADR-015: Enforce Code Quality with Ruff, Pyright, and Pytest

### Status
Accepted

### Context
Maintaining high code quality, consistent formatting, strict static typing, and high test coverage is essential for a complex multi-package monorepo.

### Decision
Standardize on:
- **Ruff** for ultra-fast linting and code formatting.
- **Pyright** in standard mode for strict static type checking.
- **Pytest** with `pytest-asyncio` for automated testing.

### Alternatives Considered
1. *Flake8 + Black + isort:* Replaced entirely by Ruff for significantly faster execution and unified configuration in `pyproject.toml`.
2. *Mypy:* Pyright is selected for better performance, excellent IDE integration, and accurate Pydantic v2 / SQLAlchemy 2.0 type inference.

### Consequences
- Rapid feedback loops during development and CI checks.
- Enforced type safety across all domain interfaces and data models.
- Consistent, automated code style enforcement.

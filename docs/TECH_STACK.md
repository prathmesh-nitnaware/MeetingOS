# MeetingOS Technology Stack Specification

**Version:** 1.0.0  
**Status:** Authoritative Specification  
**Date:** 2026-08-25  

---

## 1. Core Technology Matrix

| Layer | Technology | Version / Standard | Role & Justification |
|---|---|---|---|
| **Runtime Language** | **Python** | `3.12` | Standard runtime across all backend, NLP, and worker code. |
| **Package & Env Manager** | **uv** | Latest stable | High-performance Python virtual environment and dependency resolver. |
| **Backend API Framework** | **FastAPI** | `>=0.115.0` | Async REST API (`/api/v1`), automatic OpenAPI documentation, Pydantic v2 integration. |
| **Data Validation & CMF** | **Pydantic** | `v2.x` | Strict type validation, serialization/deserialization for Common Meeting Format. |
| **Database & ORM** | **SQLAlchemy** | `2.0.x` | Async database access via `asyncpg` and sync access via `psycopg3`. |
| **Database Migrations** | **Alembic** | `>=1.13.0` | Declarative, versioned relational and vector schema migrations. |
| **Primary Database** | **PostgreSQL** | `16` | ACID relational storage, relational knowledge graph, and primary source of truth. |
| **Vector Search Extension** | **pgvector** | `>=0.3.0` | In-database dense vector similarity search (`HNSW` / `IVFFlat` indexes). |
| **Asynchronous Task Queue** | **Celery** | `>=5.4.0` | Distributed asynchronous task execution for long-running speech & NLP jobs. |
| **Message Broker & Cache** | **Redis** | `7.x` | High-throughput broker for Celery and in-memory cache. |
| **Speech Recognition (ASR)** | **faster-whisper** | Candidate (`BaseASR`) | Local CTranslate2-based Whisper inference with int8 quantization support. |
| **Embeddings** | **sentence-transformers** | Candidate (`BaseEmbedder`) | Configurable dense sentence embeddings for transcript semantic search. |
| **Frontend Framework** | **React + Vite + TypeScript** | Phase 6 | Modern, componentized web user interface (deferred to Phase 6). |
| **Linter & Formatter** | **Ruff** | `>=0.6.0` | Ultra-fast Python linter and formatter. |
| **Static Type Checker** | **Pyright** | Standard Mode | Strict static type checking across all monorepo packages and apps. |
| **Testing Framework** | **Pytest** | `>=8.0.0` | Unit, integration, and mock provider testing with `pytest-asyncio`. |

---

## 2. Environment & Dependency Management Strategy

### 2.1 Python Runtime Standard
* **Standard Version:** **Python 3.12**.
* **Policy:** Python 3.14 (detected on host) is strictly forbidden for project dependency management due to missing pre-compiled binary wheels for PyTorch, pyannote, and C-extensions.
* **Tooling:** All local virtual environments are managed using `uv`:
  ```bash
  uv venv --python 3.12 .venv
  uv pip install -e ".[dev]"
  ```

### 2.2 Dependency Philosophy & Phasing
To prevent dependency bloat and installation fragility:
1. **Core dependencies** (`fastapi`, `pydantic`, `sqlalchemy`, `alembic`, `redis`, `celery`) are locked in `pyproject.toml`.
2. **Heavy ML/Speech dependencies** (`torch`, `faster-whisper`, `transformers`, `pyannote.audio`) are encapsulated within `packages/speech` and `packages/nlp` behind provider interfaces and introduced only when implementing those specific phases.
3. **Deterministic Mock Providers** are used for all unit tests to allow complete test execution on standard CI runners without GPUs or heavy ML packages.

---

## 3. Infrastructure & Docker Strategy

### 3.1 Local Development Services (`docker-compose.yml`)
Local infrastructure runs via Docker to ensure exact parity with production environments:
* **`postgres` service:** `pgvector/pgvector:pg16` exposing port `5432`.
* **`redis` service:** `redis:7-alpine` exposing port `6379`.

### 3.2 Containerization Architecture
* **Application Services:** `apps/api` and `workers/` will provide standalone multi-stage Dockerfiles based on `python:3.12-slim` containing `ffmpeg` and necessary system runtimes.
* **Storage Volumes:** Persistent named volumes (`pgdata`, `redisdata`) ensure data retention across container restarts.

---

## 4. Hardware Acceleration & Compute Strategy (GPU / CPU)

* **Target Hardware Context:** Development environments may have limited GPU resources (e.g. 4GB VRAM GTX 1650 or CPU-only laptops).
* **ASR Execution:** Default local target is `faster-whisper` configured for `cpu` or `cuda` with `int8` / `float16` compute types.
* **Transformers & Embeddings:** Embeddings default to lightweight models (e.g. `all-MiniLM-L6-v2`) to fit comfortably within memory constraints.
* **Pluggability:** Model providers must gracefully fall back to CPU execution or mock providers when CUDA devices are unavailable or insufficient.

---

## 5. Code Quality & Developer Tooling

1. **Ruff:** Configured for PEP 8 compliance, unused imports (`F401`), bugbear antipatterns (`B`), modern Python upgrades (`UP`), and consistent double-quote formatting.
2. **Pyright:** Enforces strict type annotations on all public functions, classes, and Pydantic schemas.
3. **Pytest & Asyncio:** All async database and API tests use `pytest-asyncio` with `asyncio_mode = "auto"`.

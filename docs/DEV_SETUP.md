# MeetingOS Development Setup

## 1. Development principle

Start with a modular monorepo. Do not prematurely split every component into microservices.

## 2. Suggested repository structure

```text
meetingos/
├── apps/
│   ├── api/
│   └── web/
├── packages/
│   ├── common/
│   ├── ingestion/
│   ├── speech/
│   ├── nlp/
│   ├── memory/
│   ├── retrieval/
│   └── reasoning/
├── workers/
├── evaluation/
├── datasets/
├── tests/
├── docs/
└── scripts/
```

The exact language/framework choices should be finalized in an ADR before implementation.

## 3. Proposed infrastructure

The project specification proposes PostgreSQL + pgvector for vector memory.

Other components should be selected according to:
- Python ML ecosystem compatibility
- deployment simplicity
- GPU availability
- graph requirements
- team skill
- evaluation needs

Do not introduce a dedicated graph database unless the workload justifies it. PostgreSQL can initially represent graph relationships relationally.

## 4. Local environment

Required categories:
- application runtime
- PostgreSQL
- pgvector
- object/file storage for development
- worker/job execution
- optional GPU runtime for speech/model workloads

## 5. Environment variables

Keep secrets out of source control.

Example categories:

```text
DATABASE_URL=
OBJECT_STORAGE_URL=
MODEL_CACHE_DIR=
LLM_API_KEY=
EMBEDDING_MODEL=
ASR_MODEL=
LOG_LEVEL=
```

Exact variables should be defined by the implementation.

## 6. Development workflow

1. Create feature branch.
2. Update relevant design document if architecture changes.
3. Add tests.
4. Run formatting/linting/type checks.
5. Run unit tests.
6. Run relevant integration tests.
7. Update documentation.
8. Open pull request.

## 7. Definition of done

A feature is done when:
- behavior is implemented
- tests exist
- failure cases are considered
- observability exists where needed
- API/schema changes are documented
- evidence/provenance is preserved for memory features
- evaluation is added for ML behavior where applicable

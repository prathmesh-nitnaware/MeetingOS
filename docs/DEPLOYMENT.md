# MeetingOS Production Deployment & Operations Guide

This guide covers production deployment, infrastructure topology, database management, and maintenance workflows for MeetingOS.

---

## 1. System Topology

```
                  Internet / Clients
                          │
                          ▼
            [ Frontend Container (Nginx:80) ]
              │                          │
              ▼ (Static SPA)             ▼ (Proxy /api/*)
         React Client           [ FastAPI Backend (:8000) ]
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
[ PostgreSQL (pgvector) ]         [ Redis Broker ]                [ Cloud AI APIs ]
   - 15 Relational Tables            - Celery Queue Broker           - OpenAI / Claude / Gemini
   - Semantic Embeddings             - Rate Limiting State           - Local Embedders
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               ▼                         ▼                         ▼
      [ worker-asr ]             [ worker-nlp ]           [ worker-embedding ]
      (Audio Ingestion)        (Fact Extraction)          (pgvector Indexing)
               │                         │
               ▼                         ▼
      [ worker-sync ]           [ worker-default ]
     (Connector Sync)           (General Async Jobs)
```

---

## 2. Environment Configuration Contract

Copy `.env.example` to `.env` and configure mandatory variables:

```bash
# Core Environment
APP_ENV=production
APP_DEBUG=false
MEETINGOS_SECRET_KEY=A_Strong_Random_Production_Secret_Key_64_Bytes!
MEETINGOS_ALLOWED_ORIGINS=https://app.meetingos.internal,https://admin.meetingos.internal

# PostgreSQL + pgvector
DATABASE_URL=postgresql+asyncpg://meetingos_user:YourSecurePassword@postgres:5432/meetingos_prod

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# AI Provider Credentials (Optional / Configured)
MEETINGOS_EMBEDDING_PROVIDER=local
MEETINGOS_REASONER_PROVIDER=local
MEETINGOS_OPENAI_API_KEY=sk-...
MEETINGOS_ANTHROPIC_API_KEY=sk-ant-...
MEETINGOS_GEMINI_API_KEY=AIza...
```

---

## 3. Launching the Production Stack

```bash
# Build and start all 9 containers in detached mode
docker compose -f docker-compose.prod.yml up -d --build

# View real-time aggregated logs
docker compose -f docker-compose.prod.yml logs -f

# Check container health status
docker compose -f docker-compose.prod.yml ps
```

---

## 4. Database Migrations (Alembic)

```bash
# Run latest database migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Inspect migration history
docker compose -f docker-compose.prod.yml exec api alembic current
```

---

## 5. Backup & Disaster Recovery

### Creating a Full Verified Backup

```bash
# Dry-run validation
python scripts/backup.py --dry-run

# Full database dump with SHA-256 manifest
python scripts/backup.py --output data/backups/meetingos_backup_$(date +%Y%m%d).json
```

### Restoring from Backup

```bash
# Dry-run validation of backup archive
python scripts/restore.py --input data/backups/meetingos_backup_20260901.json --dry-run

# Restore into database
python scripts/restore.py --input data/backups/meetingos_backup_20260901.json
```

---

## 6. Health & Observability Endpoints

| Endpoint | Method | Role | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/health` | `GET` | Public | Core service and database connectivity check |
| `/api/v1/dashboard` | `GET` | Viewer+ | High-level organizational memory metrics |
| `/api/v1/admin/metrics` | `GET` | Admin | Latency percentiles and Prometheus-format metrics |
| `/api/v1/admin/providers/status` | `GET` | Admin | Active AI provider configuration & health |
| `/api/v1/traces` | `GET` | Member+ | Multi-agent execution traces with redacted credentials |

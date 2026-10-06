# MeetingOS Horizontal Scaling & Asynchronous Architecture

MeetingOS leverages **Celery**, **Redis**, and specialized worker queues for horizontally scalable meeting ingestion, NLP fact extraction, embedding generation, and external connector synchronization.

---

## 1. Queue Separation Architecture

Tasks are divided into dedicated Celery queues to prevent fast sync jobs from blocking long-running audio transcriptions:

```
FastAPI Ingestion Endpoint / Connectors
                   │
                   ▼
              Redis Broker
      ┌────────────┼────────────┬────────────┐
      ▼            ▼            ▼            ▼
[meetingos.asr] [meetingos.nlp] [meetingos.embedding] [meetingos.sync]
      │            │            │            │
      ▼            ▼            ▼            ▼
ASR GPU Worker  NLP Worker   Vector Worker  Connector Worker
```

### Dedicated Queues

| Queue Name | Responsibilities | Target Hardware | Default Workers |
| :--- | :--- | :--- | :--- |
| `meetingos.asr` | ASR speech transcription & pyannote diarization | GPU (CUDA / TensorRT) | `MEETINGOS_ASR_WORKERS=1` |
| `meetingos.nlp` | NER, decision/commitment extraction, relation graphs | CPU / Multicore | `MEETINGOS_NLP_WORKERS=2` |
| `meetingos.embedding` | Vector embedding generation & batch pgvector upserts | GPU / CPU | `MEETINGOS_EMBEDDING_WORKERS=2` |
| `meetingos.sync` | Microsoft Teams, Zoom, Google Meet synchronization | CPU / Network I/O | `2` |

---

## 2. Worker Scaling Commands

```bash
# Start GPU-specialized ASR worker
celery -A workers.celery_app worker -Q meetingos.asr -c 1 --loglevel=info

# Start NLP and Vector workers
celery -A workers.celery_app worker -Q meetingos.nlp,meetingos.embedding -c 4 --loglevel=info

# Start Connector sync worker
celery -A workers.celery_app worker -Q meetingos.sync,default -c 2 --loglevel=info
```

---

## 3. Reliability & Idempotency
- **Late Acknowledgments:** `task_acks_late=True` ensures tasks are re-queued if a worker crashes.
- **Timeouts:** 1-hour hard limit (`task_time_limit=3600`) and 55-minute soft limit (`task_soft_time_limit=3300`).
- **Telemetry:** `WorkerTelemetryTracker` tracks task success rates, retry counts, queue depth, and throughput in real time.

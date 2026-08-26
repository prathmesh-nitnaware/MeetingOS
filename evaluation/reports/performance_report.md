# MeetingOS Performance & Load Benchmark Report

- **Generated:** 2026-08-26 04:38:09 UTC
- **Environment:** In-memory SQLite + AsyncSession + Mock Embedders/Reasoners (Deterministic)
- **Dataset Scale:** 13 meetings (48 segments)

## 1. Ingestion Throughput

| Metric | Result |
| :--- | :--- |
| **Total Ingested Meetings** | 13 |
| **Total Ingested Segments** | 48 |
| **Total Ingestion Duration** | 1.5843 s |
| **Ingestion Throughput** | **8.21 meetings/sec** |
| **Segment Processing Rate** | **30.3 segments/sec** |

## 2. Hybrid Retrieval Latency

| Latency Percentile | Time (ms) |
| :--- | :--- |
| **Average** | 44.902 ms |
| **p50 (Median)** | 44.262 ms |
| **p95** | 56.698 ms |
| **p99** | 56.698 ms |

## 3. Query Latency Comparison

| System | Average (ms) | p50 (ms) | p95 (ms) |
| :--- | :---: | :---: | :---: |
| **Unified RAG Pipeline** | 58.2 ms | 55.582 ms | 156.302 ms |
| **Multi-Agent Orchestrator** | 40.241 ms | 37.087 ms | 64.921 ms |

## 4. Multi-Agent Orchestration Breakdown (Average ms per Stage)

| Stage / Specialist Agent | Avg Duration (ms) |
| :--- | :---: |
| **Planner Agent** | 0.28 ms |
| **Retrieval Agent** | 35.95 ms |
| **Temporal Agent** | 17.65 ms |
| **Graph Agent** | 20.96 ms |
| **Evidence Validation Agent** | 0.01 ms |
| **Answer Synthesis Agent** | 0.79 ms |

## 5. Concurrent Query Behavior

| Parameter | Value |
| :--- | :--- |
| **Parallel Concurrent Queries** | 5 queries |
| **Total Wall Clock Time** | 135.617 ms |
| **Effective Throughput** | **36.87 queries/sec** |
| **All Completed Successfully** | True |

---
*Report generated automatically by `evaluation/benchmark.py`.*

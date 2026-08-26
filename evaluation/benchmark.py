import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.agents.orchestrator import AgentOrchestrator
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import EvidenceItem, Meeting
from packages.memory.repository import MeetingRepository, init_db
from packages.nlp.mock import MockEmbedder
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.mock import MockReasoner
from packages.reasoning.qa import RAGPipeline
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.retrieval.search import HybridSearchEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from evaluation.dataset import load_extended_meetings


async def run_performance_benchmark() -> dict[str, Any]:
    """Execute deterministic offline performance and load benchmark."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    await init_db(engine)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    report_data: dict[str, Any] = {}

    async with session_maker() as session:
        repo = MeetingRepository(session)
        embedder = MockEmbedder()
        nlp_pipeline = NLPExtractionPipeline()
        temporal_engine = TemporalIntelligenceEngine(session)

        # 1. Measure Ingestion Throughput
        meetings_data = load_extended_meetings()
        t0 = time.perf_counter()
        total_segments = 0

        for m_dict in meetings_data:
            meeting = Meeting.model_validate(m_dict)
            meeting.processing_status = ProcessingStatus.SUCCEEDED
            await repo.create_meeting(meeting)
            total_segments += len(meeting.segments)

            embeddings = []
            evidence_records = []
            for seg in meeting.segments:
                vecs = await embedder.embed([seg.text])
                embeddings.append(("segment", seg.segment_id, seg.text, vecs[0]))
                evidence_records.append(
                    EvidenceItem(
                        meeting_id=meeting.meeting_id,
                        segment_id=seg.segment_id,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text_snapshot=seg.text,
                        source_type=SourceType.AUDIO_WAV,
                    )
                )
            await repo.save_embeddings(meeting.meeting_id, embeddings)
            await repo.save_evidence_records(meeting.meeting_id, evidence_records)

            nlp_result = await nlp_pipeline.process_transcript(
                meeting_id=meeting.meeting_id,
                segments=meeting.segments,
                meeting_date=meeting.meeting_date,
            )
            await repo.save_nlp_extraction_results(meeting.meeting_id, nlp_result)
            await temporal_engine.reconcile_meeting_lifecycle(meeting.meeting_id)

        await session.commit()
        t_ingest = time.perf_counter() - t0

        meetings_per_sec = len(meetings_data) / max(0.001, t_ingest)
        segments_per_sec = total_segments / max(0.001, t_ingest)

        report_data["ingestion"] = {
            "total_meetings": len(meetings_data),
            "total_segments": total_segments,
            "duration_seconds": round(t_ingest, 4),
            "meetings_per_second": round(meetings_per_sec, 2),
            "segments_per_second": round(segments_per_sec, 2),
        }

        # 2. Database Retrieval Latency
        search_engine = HybridSearchEngine(session, embedder=embedder)
        sample_queries = [
            "PostgreSQL pgvector database",
            "Redis timeout issue",
            "database schema migration deadline",
            "Kubernetes cluster deployment",
            "JWT authentication roles",
        ]

        retrieval_latencies: list[float] = []
        for q in sample_queries * 4:  # 20 searches
            t_s = time.perf_counter()
            await search_engine.search(q)
            retrieval_latencies.append((time.perf_counter() - t_s) * 1000)

        retrieval_latencies.sort()
        report_data["retrieval"] = {
            "avg_ms": round(sum(retrieval_latencies) / len(retrieval_latencies), 3),
            "p50_ms": round(retrieval_latencies[len(retrieval_latencies) // 2], 3),
            "p95_ms": round(retrieval_latencies[int(len(retrieval_latencies) * 0.95)], 3),
            "p99_ms": round(retrieval_latencies[-1], 3),
        }

        # 3. Pipeline Query Latency (Single Agent / RAG)
        rag = RAGPipeline(session, reasoner=MockReasoner())
        rag_latencies: list[float] = []
        for q in sample_queries * 2:
            t_s = time.perf_counter()
            await rag.answer_question(q)
            rag_latencies.append((time.perf_counter() - t_s) * 1000)

        rag_latencies.sort()
        report_data["rag_pipeline"] = {
            "avg_ms": round(sum(rag_latencies) / len(rag_latencies), 3),
            "p50_ms": round(rag_latencies[len(rag_latencies) // 2], 3),
            "p95_ms": round(rag_latencies[int(len(rag_latencies) * 0.95)], 3),
        }

        # 4. Multi-Agent Orchestrator Latency
        orchestrator = AgentOrchestrator(session, reasoner=MockReasoner())
        agent_latencies: list[float] = []
        stage_times: dict[str, list[float]] = {
            "planner": [],
            "retrieval": [],
            "temporal": [],
            "graph": [],
            "evidence": [],
            "answer": [],
        }

        for q in sample_queries * 2:
            t_s = time.perf_counter()
            res = await orchestrator.query(q)
            agent_latencies.append((time.perf_counter() - t_s) * 1000)
            for item in res.trace:
                if item.agent in stage_times and item.duration_seconds is not None:
                    stage_times[item.agent].append(item.duration_seconds * 1000)

        agent_latencies.sort()
        report_data["agentic_orchestrator"] = {
            "avg_ms": round(sum(agent_latencies) / len(agent_latencies), 3),
            "p50_ms": round(agent_latencies[len(agent_latencies) // 2], 3),
            "p95_ms": round(agent_latencies[int(len(agent_latencies) * 0.95)], 3),
            "stages_avg_ms": {k: round(sum(v) / max(1, len(v)), 3) for k, v in stage_times.items()},
        }

        # 5. Concurrent Query Behavior (5 parallel requests)
        t_c = time.perf_counter()
        concurrent_queries = [
            orchestrator.query("What database was chosen?"),
            orchestrator.query("Who investigated Redis timeout?"),
            orchestrator.query("What is the schema migration deadline?"),
            orchestrator.query("Who owns Kubernetes setup?"),
            orchestrator.query("What auth mechanism is used?"),
        ]
        results = await asyncio.gather(*concurrent_queries)
        t_c_dur = (time.perf_counter() - t_c) * 1000

        report_data["concurrent_queries"] = {
            "parallel_count": len(concurrent_queries),
            "total_wall_clock_ms": round(t_c_dur, 3),
            "effective_throughput_qps": round(
                len(concurrent_queries) / max(0.001, t_c_dur / 1000), 2
            ),
            "all_succeeded": len(results) == 5 and all(r.answer for r in results),
        }

    await engine.dispose()

    # Generate Markdown Performance Report
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "performance_report.md"

    md = f"""# MeetingOS Performance & Load Benchmark Report

- **Generated:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Environment:** In-memory SQLite + AsyncSession + Mock Embedders/Reasoners (Deterministic)
- **Dataset Scale:** {report_data["ingestion"]["total_meetings"]} meetings ({report_data["ingestion"]["total_segments"]} segments)

## 1. Ingestion Throughput

| Metric | Result |
| :--- | :--- |
| **Total Ingested Meetings** | {report_data["ingestion"]["total_meetings"]} |
| **Total Ingested Segments** | {report_data["ingestion"]["total_segments"]} |
| **Total Ingestion Duration** | {report_data["ingestion"]["duration_seconds"]} s |
| **Ingestion Throughput** | **{report_data["ingestion"]["meetings_per_second"]} meetings/sec** |
| **Segment Processing Rate** | **{report_data["ingestion"]["segments_per_second"]} segments/sec** |

## 2. Hybrid Retrieval Latency

| Latency Percentile | Time (ms) |
| :--- | :--- |
| **Average** | {report_data["retrieval"]["avg_ms"]} ms |
| **p50 (Median)** | {report_data["retrieval"]["p50_ms"]} ms |
| **p95** | {report_data["retrieval"]["p95_ms"]} ms |
| **p99** | {report_data["retrieval"]["p99_ms"]} ms |

## 3. Query Latency Comparison

| System | Average (ms) | p50 (ms) | p95 (ms) |
| :--- | :---: | :---: | :---: |
| **Unified RAG Pipeline** | {report_data["rag_pipeline"]["avg_ms"]} ms | {report_data["rag_pipeline"]["p50_ms"]} ms | {report_data["rag_pipeline"]["p95_ms"]} ms |
| **Multi-Agent Orchestrator** | {report_data["agentic_orchestrator"]["avg_ms"]} ms | {report_data["agentic_orchestrator"]["p50_ms"]} ms | {report_data["agentic_orchestrator"]["p95_ms"]} ms |

## 4. Multi-Agent Orchestration Breakdown (Average ms per Stage)

| Stage / Specialist Agent | Avg Duration (ms) |
| :--- | :---: |
| **Planner Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["planner"]} ms |
| **Retrieval Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["retrieval"]} ms |
| **Temporal Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["temporal"]} ms |
| **Graph Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["graph"]} ms |
| **Evidence Validation Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["evidence"]} ms |
| **Answer Synthesis Agent** | {report_data["agentic_orchestrator"]["stages_avg_ms"]["answer"]} ms |

## 5. Concurrent Query Behavior

| Parameter | Value |
| :--- | :--- |
| **Parallel Concurrent Queries** | {report_data["concurrent_queries"]["parallel_count"]} queries |
| **Total Wall Clock Time** | {report_data["concurrent_queries"]["total_wall_clock_ms"]} ms |
| **Effective Throughput** | **{report_data["concurrent_queries"]["effective_throughput_qps"]} queries/sec** |
| **All Completed Successfully** | {report_data["concurrent_queries"]["all_succeeded"]} |

---
*Report generated automatically by `evaluation/benchmark.py`.*
"""
    with report_file.open("w", encoding="utf-8") as f:
        f.write(md)

    return report_data

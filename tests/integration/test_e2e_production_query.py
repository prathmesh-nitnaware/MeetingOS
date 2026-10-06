from datetime import UTC, datetime

import pytest
from packages.agents.orchestrator import AgentOrchestrator
from packages.agents.traces import global_trace_store
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import EvidenceItem, Meeting, Participant, TranscriptSegment
from packages.memory.repository import MeetingRepository, init_db
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.providers.embeddings import LocalSemanticEmbedder
from packages.providers.reasoning import LocalEvidenceReasoner
from packages.reasoning.temporal import TemporalIntelligenceEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_e2e_production_query_pipeline():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    await init_db(engine)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    local_embedder = LocalSemanticEmbedder(dimension=384)
    local_reasoner = LocalEvidenceReasoner()
    nlp_pipeline = NLPExtractionPipeline()

    meeting_id = "e2e-prod-meet-001"
    meeting_date = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)

    segments = [
        TranscriptSegment(
            segment_id="e2e-seg-001",
            speaker_id="Alex",
            start_time=0.0,
            end_time=15.0,
            text="Welcome everyone. We need to finalize our primary organizational memory database store.",
            sequence=1,
        ),
        TranscriptSegment(
            segment_id="e2e-seg-002",
            speaker_id="Sarah",
            start_time=15.0,
            end_time=35.0,
            text="After benchmarking pgvector, we decided to adopt PostgreSQL with pgvector for the memory layer.",
            sequence=2,
        ),
        TranscriptSegment(
            segment_id="e2e-seg-003",
            speaker_id="David",
            start_time=35.0,
            end_time=50.0,
            text="Agreed. Sarah will lead the database deployment by September 15th.",
            sequence=3,
        ),
    ]

    meeting = Meeting(
        meeting_id=meeting_id,
        title="Architecture Decision Review",
        meeting_date=meeting_date,
        source_type=SourceType.AUDIO_WAV,
        processing_status=ProcessingStatus.SUCCEEDED,
        participants=[
            Participant(canonical_name="Alex"),
            Participant(canonical_name="Sarah"),
            Participant(canonical_name="David"),
        ],
        segments=segments,
    )

    async with session_maker() as session:
        repo = MeetingRepository(session)
        temporal_engine = TemporalIntelligenceEngine(session)

        # 1. Ingest Meeting
        await repo.create_meeting(meeting)

        # 2. Embeddings & Evidence
        embeddings = []
        evidence_records = []
        for seg in segments:
            vecs = await local_embedder.embed([seg.text])
            embeddings.append(("segment", seg.segment_id, seg.text, vecs[0]))
            evidence_records.append(
                EvidenceItem(
                    meeting_id=meeting_id,
                    segment_id=seg.segment_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text_snapshot=seg.text,
                    source_type=SourceType.AUDIO_WAV,
                )
            )
        await repo.save_embeddings(meeting_id, embeddings)
        await repo.save_evidence_records(meeting_id, evidence_records)

        # 3. NLP Extraction
        nlp_res = await nlp_pipeline.process_transcript(meeting_id, segments, meeting_date)
        await repo.save_nlp_extraction_results(meeting_id, nlp_res)
        await temporal_engine.reconcile_meeting_lifecycle(meeting_id)
        await session.commit()

        # 4. Multi-Agent Orchestrated QA
        orchestrator = AgentOrchestrator(session, reasoner=local_reasoner)
        orchestrator.retrieval_agent.search_engine.embedder = local_embedder

        # Query 1: Grounded question
        q1 = "What database was adopted for the organizational memory layer?"
        res1 = await orchestrator.query(q1)

        assert res1.answer is not None
        assert "PostgreSQL" in res1.answer or "pgvector" in res1.answer
        assert res1.confidence >= 0.5
        assert len(res1.evidence) >= 1
        assert any(e.segment_id == "e2e-seg-002" for e in res1.evidence)

        # Query 2: Ungrounded / unsupported question
        q2 = "What was the budget allocated for quantum computing research in 2030?"
        res2 = await orchestrator.query(q2)

        assert res2.answer is not None
        # Must refuse or indicate lack of evidence
        assert (
            res2.confidence <= 0.6
            or "insufficient" in res2.answer.lower()
            or "not mention" in res2.answer.lower()
        )

        # Verify trace persistence and secret sanitization
        traces = global_trace_store.list_traces(limit=20)
        assert len(traces) >= 1
        for tr in traces:
            assert tr.trace_id is not None
            assert tr.total_latency_ms >= 0
            # Assert no sensitive bearer keys or credentials leaked into traces
            tr_dump = tr.model_dump_json()
            assert "bearer" not in tr_dump.lower() or "[REDACTED]" in tr_dump

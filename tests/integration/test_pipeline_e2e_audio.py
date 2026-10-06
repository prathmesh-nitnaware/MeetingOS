from datetime import UTC, datetime
from pathlib import Path

import pytest
from packages.agents.orchestrator import AgentOrchestrator
from packages.agents.traces import global_trace_store
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import EvidenceItem, Meeting, MeetingMetadata
from packages.ingestion.pipeline import IngestionPipeline
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.providers.embeddings import LocalSemanticEmbedder
from packages.providers.reasoning import LocalEvidenceReasoner
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.speech.mock import MockASR, MockDiarizer
from sqlalchemy.ext.asyncio import AsyncSession
from tests.fixtures.audio_generator import generate_synthetic_meeting_wav


@pytest.mark.asyncio
async def test_end_to_end_audio_pipeline(tmp_path: Path, test_db_session: AsyncSession):
    """End-to-end integration test validating complete workflow from audio file to agentic QA."""
    # 1. Generate real synthetic WAV audio meeting file
    audio_path = tmp_path / "executive_sync.wav"
    generate_synthetic_meeting_wav(audio_path, duration_seconds=5.0, sample_rate=16000)
    assert audio_path.exists()
    assert audio_path.stat().st_size > 1000

    # 2. Ingestion & Speech Processing
    ingestion = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())
    segments, speakers, duration = await ingestion.process_file(
        audio_path, source_type=SourceType.AUDIO_WAV
    )
    assert len(segments) > 0
    assert len(speakers) > 0
    assert duration > 0

    # 3. Create Meeting Model
    meeting_id = "meet-audio-e2e-001"
    meeting = Meeting(
        meeting_id=meeting_id,
        title="Executive Architecture Sync",
        meeting_date=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        source_type=SourceType.AUDIO_WAV,
        metadata=MeetingMetadata(source_filename=audio_path.name),
        duration_seconds=duration,
        processing_status=ProcessingStatus.RUNNING,
        segments=segments,
        speakers=speakers,
    )

    # 4. Save to Repository
    repo = MeetingRepository(test_db_session)
    await repo.create_meeting(meeting)

    # 5. Generate & Save Embeddings + Evidence
    embedder = LocalSemanticEmbedder(dimension=384)
    embeddings = []
    evidence_items = []
    for seg in segments:
        vecs = await embedder.embed([seg.text])
        embeddings.append(("segment", seg.segment_id, seg.text, vecs[0]))
        evidence_items.append(
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
    await repo.save_evidence_records(meeting_id, evidence_items)

    # 6. NLP Extraction
    nlp_pipeline = NLPExtractionPipeline()
    nlp_result = await nlp_pipeline.process_transcript(
        meeting_id=meeting_id,
        segments=segments,
        meeting_date=meeting.meeting_date,
    )
    await repo.save_nlp_extraction_results(meeting_id, nlp_result)

    # 7. Temporal Reconciliation
    temporal_engine = TemporalIntelligenceEngine(test_db_session)
    await temporal_engine.reconcile_meeting_lifecycle(meeting_id)

    meeting.processing_status = ProcessingStatus.SUCCEEDED
    await test_db_session.commit()

    # 8. Multi-Agent Reasoning Query Execution
    reasoner = LocalEvidenceReasoner()
    orchestrator = AgentOrchestrator(test_db_session, reasoner=reasoner)
    orchestrator.retrieval_agent.search_engine.embedder = embedder

    query = "What database was adopted for MeetingOS?"
    res = await orchestrator.query(query)

    assert res.confidence > 0.0
    assert len(res.evidence) > 0
    assert len(res.citations) > 0
    assert res.trace_id is not None
    assert not res.insufficient_evidence

    # Verify trace persisted in global trace store
    saved_trace = global_trace_store.get_trace(res.trace_id)
    assert saved_trace is not None
    assert saved_trace.query == query
    assert len(saved_trace.steps) >= 4

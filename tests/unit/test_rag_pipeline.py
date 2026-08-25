from datetime import UTC, datetime

import pytest
from packages.common.enums import DecisionStatus, EntityType, SourceType
from packages.common.models import (
    ExtractedDecision,
    ExtractedEntity,
    Meeting,
    TranscriptSegment,
)
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionResult
from packages.reasoning.planner import QueryPlan
from packages.reasoning.qa import RAGPipeline


@pytest.mark.asyncio
async def test_rag_pipeline_grounded_answer(test_repository: MeetingRepository):
    # Ingest meeting with transcript, embeddings, facts
    dt = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)
    meeting = Meeting(
        meeting_id="meet-rag-01",
        title="Architecture Decision Meeting",
        meeting_date=dt,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="seg-rag-1",
                sequence=0,
                speaker_id="spk_rahul",
                start_time=12.5,
                end_time=25.0,
                text="Rahul Verma: We evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL and pgvector for MeetingOS.",
            )
        ],
    )
    await test_repository.create_meeting(meeting)
    await test_repository.save_embeddings(
        "meet-rag-01",
        [
            (
                "segment",
                "seg-rag-1",
                "Rahul Verma: We evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL and pgvector for MeetingOS.",
                [0.9, 0.1, 0.2],
            )
        ],
    )
    await test_repository.save_nlp_extraction_results(
        "meet-rag-01",
        NLPExtractionResult(
            meeting_id="meet-rag-01",
            entities=[
                ExtractedEntity(
                    entity_id="ent-postgres", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
                ),
                ExtractedEntity(
                    entity_id="ent-mongo", name="MongoDB", entity_type=EntityType.TECHNOLOGY
                ),
            ],
            decisions=[
                ExtractedDecision(
                    decision_id="dec-pg",
                    subject="Adopt PostgreSQL with pgvector",
                    status=DecisionStatus.APPROVED,
                    meeting_id="meet-rag-01",
                    evidence_segment_id="seg-rag-1",
                )
            ],
        ),
    )

    rag = RAGPipeline(test_repository.session)

    # Ask grounded question
    res = await rag.answer_question("What decisions did we make about the database?")
    assert len(res.answer) > 10
    assert "PostgreSQL" in res.answer
    assert len(res.evidence) >= 1
    assert res.evidence[0].meeting_id == "meet-rag-01"
    assert res.evidence[0].start_time == 12.5
    assert res.evidence[0].end_time == 25.0
    assert res.confidence > 0.8
    assert len(res.reasoning_path) >= 2


@pytest.mark.asyncio
async def test_rag_pipeline_unsupported_question_faithfulness(test_repository: MeetingRepository):
    rag = RAGPipeline(test_repository.session)
    res = await rag.answer_question("What is our rocket propulsion architecture?")
    assert "does not establish an answer" in res.answer
    assert len(res.evidence) == 0
    assert res.confidence == 0.0


@pytest.mark.asyncio
async def test_rag_pipeline_with_plan_override(test_repository: MeetingRepository):
    rag = RAGPipeline(test_repository.session)
    custom_plan = QueryPlan(person="Rahul", topic="Database", type="decision", intent="qa")
    res = await rag.answer_question("What did Rahul say?", plan_override=custom_plan)
    assert res.query_plan.person == "Rahul"
    assert res.query_plan.topic == "Database"

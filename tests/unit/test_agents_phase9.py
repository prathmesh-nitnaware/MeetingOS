from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from packages.agents.answer import AnswerAgent
from packages.agents.context import AgentContext, AgentEvidence
from packages.agents.evidence import EvidenceAgent
from packages.agents.graph import GraphAgent
from packages.agents.orchestrator import AgentOrchestrator
from packages.agents.planner import PlannerAgent
from packages.agents.retrieval import RetrievalAgent
from packages.agents.temporal import TemporalAgent
from packages.common.enums import ProcessingStatus
from packages.common.models import (
    EvidenceItem,
    Meeting,
    Participant,
    SpeakerInfo,
    TranscriptSegment,
)
from packages.memory.repository import MeetingRepository
from packages.nlp.mock import MockEmbedder
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.reasoning.qa import QueryPlan
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_data(test_db_session: AsyncSession) -> Meeting:
    repo = MeetingRepository(test_db_session)
    embedder = MockEmbedder()
    nlp_pipeline = NLPExtractionPipeline()

    meeting = Meeting(
        meeting_id="meet-agent-01",
        title="PostgreSQL vs MongoDB Architecture Decision",
        meeting_date=datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC),
        participants=[
            Participant(id="p1", canonical_name="Alice Dev"),
            Participant(id="p2", canonical_name="Bob Lead"),
        ],
        speakers=[
            SpeakerInfo(speaker_id="spk_0", name="Alice Dev"),
            SpeakerInfo(speaker_id="spk_1", name="Bob Lead"),
        ],
        segments=[
            TranscriptSegment(
                segment_id="seg-1",
                sequence=0,
                speaker_id="spk_0",
                start_time=0.0,
                end_time=10.0,
                text="We decided to adopt PostgreSQL instead of MongoDB because relational integrity is critical for our transactional logs.",
            ),
            TranscriptSegment(
                segment_id="seg-2",
                sequence=1,
                speaker_id="spk_1",
                start_time=10.0,
                end_time=20.0,
                text="Yes, and Priya Sharma is the owner of this database migration task.",
            ),
        ],
    )
    meeting.processing_status = ProcessingStatus.SUCCEEDED
    await repo.create_meeting(meeting)

    # Save embeddings + evidence records so HybridSearchEngine can retrieve segments
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
                source_type=meeting.source_type,
            )
        )
    await repo.save_embeddings(meeting.meeting_id, embeddings)
    await repo.save_evidence_records(meeting.meeting_id, evidence_records)

    # Run NLP extraction
    nlp_result = await nlp_pipeline.process_transcript(
        meeting_id=meeting.meeting_id,
        segments=meeting.segments,
        meeting_date=meeting.meeting_date,
    )
    await repo.save_nlp_extraction_results(meeting.meeting_id, nlp_result)

    await test_db_session.commit()
    return meeting


@pytest.mark.asyncio
async def test_planner_agent():
    agent = PlannerAgent()
    context = AgentContext(query="Why did we adopt PostgreSQL instead of MongoDB?")
    res = await agent.run(context)
    assert res.plan is not None
    # Verify entities extracted
    ents = [e.lower() for e in res.entities]
    assert "postgresql" in ents or "mongodb" in ents
    assert any(t.agent == "planner" and t.status == "completed" for t in res.trace)


@pytest.mark.asyncio
async def test_retrieval_agent(test_db_session: AsyncSession, seed_data: Meeting):  # noqa: ARG001
    agent = RetrievalAgent(test_db_session)
    context = AgentContext(
        query="PostgreSQL MongoDB",
        plan=QueryPlan(intent="qa", type="segment", entities=["PostgreSQL", "MongoDB"]),
    )
    res = await agent.run(context)
    assert len(res.retrieved_evidence) > 0
    assert any(t.agent == "retrieval" and t.status == "completed" for t in res.trace)


@pytest.mark.asyncio
async def test_temporal_agent(test_db_session: AsyncSession, seed_data: Meeting):  # noqa: ARG001
    agent = TemporalAgent(test_db_session)
    context = AgentContext(
        query="PostgreSQL MongoDB",
        entities=["PostgreSQL"],
    )
    res = await agent.run(context)
    assert any(t.agent == "temporal" and t.status == "completed" for t in res.trace)


@pytest.mark.asyncio
async def test_graph_agent(test_db_session: AsyncSession, seed_data: Meeting):  # noqa: ARG001
    agent = GraphAgent(test_db_session)
    context = AgentContext(
        query="PostgreSQL MongoDB",
        entities=["PostgreSQL"],
    )
    res = await agent.run(context)
    assert any(t.agent == "graph" and t.status == "completed" for t in res.trace)


@pytest.mark.asyncio
async def test_evidence_agent_sufficient():
    agent = EvidenceAgent()
    context = AgentContext(
        query="Why did we adopt PostgreSQL?",
        entities=["PostgreSQL"],
        retrieved_evidence=[
            AgentEvidence(
                meeting_id="meet-agent-01",
                segment_id="seg-1",
                start_time=0.0,
                end_time=10.0,
                content="We evaluated PostgreSQL and adopted it.",
                relevance_score=0.8,
            )
        ],
    )
    res = await agent.run(context)
    assert res.insufficient_evidence is False
    assert res.support_status == "SUPPORTED"
    assert res.confidence > 0.0


@pytest.mark.asyncio
async def test_evidence_agent_insufficient():
    agent = EvidenceAgent()
    # Kubernetes is not mentioned anywhere in retrieved segments
    context = AgentContext(
        query="What did we decide about Kubernetes?",
        entities=["Kubernetes"],
        retrieved_evidence=[
            AgentEvidence(
                meeting_id="meet-agent-01",
                segment_id="seg-1",
                start_time=0.0,
                end_time=10.0,
                content="We evaluated PostgreSQL and adopted it.",
                relevance_score=0.8,
            )
        ],
    )
    res = await agent.run(context)
    assert res.insufficient_evidence is True
    assert res.support_status == "INSUFFICIENT_EVIDENCE"
    assert res.confidence == 0.0


@pytest.mark.asyncio
async def test_orchestrator_sufficient(test_db_session: AsyncSession, seed_data: Meeting):  # noqa: ARG001
    orchestrator = AgentOrchestrator(test_db_session)
    res = await orchestrator.query("Why did we adopt PostgreSQL instead of MongoDB?")
    assert res.insufficient_evidence is False
    assert "postgresql" in res.answer.lower() or "mongodb" in res.answer.lower()
    assert len(res.citations) > 0


@pytest.mark.asyncio
async def test_orchestrator_insufficient() -> None:
    """When evidence agent sees no retrieved segments, answer must be the standard insufficient message."""
    ev_agent = EvidenceAgent()
    ans_agent = AnswerAgent()

    # Context with explicitly empty evidence list and a named entity that cannot be found
    ctx = AgentContext(
        query="What did we decide about ZephyrDB?",
        entities=["ZephyrDB"],
        retrieved_evidence=[],
    )
    ctx = await ev_agent.run(ctx)
    ctx = await ans_agent.run(ctx)

    assert ctx.insufficient_evidence is True
    assert ctx.confidence == 0.0
    assert "does not establish an answer" in ctx.answer.lower()


@pytest.mark.asyncio
async def test_query_agentic_endpoint(async_client: AsyncClient):
    headers = {"Authorization": "Bearer admin-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Why did we adopt PostgreSQL?"},
        headers=headers,
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "answer" in res_data
    assert "confidence" in res_data
    assert "trace" in res_data

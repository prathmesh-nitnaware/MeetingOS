from datetime import UTC, datetime

import pytest
from packages.agents.context import AgentContext, AgentEvidence
from packages.agents.evidence import EvidenceAgent
from packages.reasoning.planner import QueryPlan


@pytest.mark.asyncio
async def test_evidence_agent_conflict_detection():
    agent = EvidenceAgent()
    context = AgentContext(
        query="Did we stick with Docker Compose or Kubernetes?",
        plan=QueryPlan(intent="qa", entities=["Docker", "Kubernetes"]),
        entities=["Docker", "Kubernetes"],
        retrieved_evidence=[
            AgentEvidence(
                meeting_id="m1",
                meeting_title="Initial Infra Sync",
                meeting_date=datetime(2026, 8, 20, tzinfo=UTC),
                segment_id="s1",
                start_time=0.0,
                end_time=10.0,
                content="We decided to use Docker Compose for local container orchestration.",
            ),
            AgentEvidence(
                meeting_id="m2",
                meeting_title="Infra Scaling Review",
                meeting_date=datetime(2026, 8, 27, tzinfo=UTC),
                segment_id="s2",
                start_time=0.0,
                end_time=10.0,
                content="We are reversing the Docker Compose decision and will migrate to Kubernetes instead of Docker Compose.",
            ),
        ],
    )

    res = await agent.run(context)

    assert not res.insufficient_evidence
    assert len(res.conflicts_detected) == 1
    conflict = res.conflicts_detected[0]
    assert conflict["earlier_meeting_id"] == "m1"
    assert conflict["later_meeting_id"] == "m2"
    assert res.retrieved_evidence[0].lifecycle_state == "superseded"
    assert res.retrieved_evidence[1].lifecycle_state == "active"


@pytest.mark.asyncio
async def test_evidence_agent_insufficient_grounding():
    agent = EvidenceAgent()
    context = AgentContext(
        query="What was decided about Apache Cassandra?",
        plan=QueryPlan(intent="qa", entities=["Cassandra"]),
        entities=["Cassandra"],
        retrieved_evidence=[
            AgentEvidence(
                meeting_id="m1",
                segment_id="s1",
                start_time=0.0,
                end_time=10.0,
                content="We evaluated PostgreSQL and MongoDB.",
            )
        ],
    )

    res = await agent.run(context)
    assert res.insufficient_evidence
    assert res.confidence == 0.0

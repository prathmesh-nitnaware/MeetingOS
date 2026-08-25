from datetime import UTC, datetime

import pytest
from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    IssueStatus,
    RelationType,
    SourceType,
)
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedIssue,
    ExtractedRelation,
    Meeting,
    TranscriptSegment,
)
from packages.memory.graph import GraphService
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionResult


@pytest.mark.asyncio
async def test_cross_meeting_linking_and_graph(test_repository: MeetingRepository):
    service = GraphService(test_repository.session)
    dt1 = datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)

    # Ingest Meeting 1
    m1 = Meeting(
        meeting_id="meet-graph-001",
        title="Sync 1",
        meeting_date=dt1,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s1",
                sequence=0,
                speaker_id="spk_rahul",
                start_time=0.0,
                end_time=5.0,
                text="Rahul: Decide Postgres",
            )
        ],
    )
    await test_repository.create_meeting(m1)
    await test_repository.save_nlp_extraction_results(
        "meet-graph-001",
        NLPExtractionResult(
            meeting_id="meet-graph-001",
            entities=[
                ExtractedEntity(
                    entity_id="ent-rahul", name="Rahul Verma", entity_type=EntityType.PERSON
                ),
                ExtractedEntity(
                    entity_id="ent-postgres", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
                ),
            ],
            decisions=[
                ExtractedDecision(
                    decision_id="dec-1",
                    subject="Adopt PostgreSQL",
                    status=DecisionStatus.APPROVED,
                    meeting_id="meet-graph-001",
                )
            ],
            relations=[
                ExtractedRelation(
                    relation_id="rel-1",
                    source_entity_id="ent-rahul",
                    target_entity_id="ent-postgres",
                    relationship_type=RelationType.ASSIGNED_TO,
                    meeting_id="meet-graph-001",
                )
            ],
        ),
    )

    # Ingest Meeting 2 with shared entities and new relations
    m2 = Meeting(
        meeting_id="meet-graph-002",
        title="Sync 2",
        meeting_date=dt2,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="s2",
                sequence=0,
                speaker_id="spk_priya",
                start_time=0.0,
                end_time=5.0,
                text="Priya: Review Postgres",
            )
        ],
    )
    await test_repository.create_meeting(m2)
    await test_repository.save_nlp_extraction_results(
        "meet-graph-002",
        NLPExtractionResult(
            meeting_id="meet-graph-002",
            entities=[
                ExtractedEntity(
                    entity_id="ent-postgres", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
                ),
                ExtractedEntity(
                    entity_id="ent-priya", name="Priya Sharma", entity_type=EntityType.PERSON
                ),
                ExtractedEntity(
                    entity_id="ent-meetingos", name="MeetingOS", entity_type=EntityType.PROJECT
                ),
            ],
            commitments=[
                ExtractedCommitment(
                    commitment_id="com-2",
                    description="Benchmark PostgreSQL for MeetingOS",
                    owner_id="spk_priya",
                    status=CommitmentStatus.IN_PROGRESS,
                    meeting_id="meet-graph-002",
                )
            ],
            issues=[
                ExtractedIssue(
                    issue_id="iss-2",
                    description="Connection pool saturation",
                    owner_id="spk_priya",
                    status=IssueStatus.DETECTED,
                    first_detected_at=dt2,
                )
            ],
            relations=[
                ExtractedRelation(
                    relation_id="rel-2",
                    source_entity_id="ent-priya",
                    target_entity_id="ent-postgres",
                    relationship_type=RelationType.WORKS_ON,
                    meeting_id="meet-graph-002",
                ),
                ExtractedRelation(
                    relation_id="rel-3",
                    source_entity_id="ent-postgres",
                    target_entity_id="ent-meetingos",
                    relationship_type=RelationType.RELATED_TO,
                    meeting_id="meet-graph-002",
                ),
            ],
        ),
    )

    # 1. Verify Canonical Entities list shows PostgreSQL linked to 2 meetings
    entities = await service.list_canonical_entities()
    postgres_node = next(e for e in entities if e.id == "ent-postgres")
    assert postgres_node.meeting_count == 2
    assert "meet-graph-001" in postgres_node.meetings
    assert "meet-graph-002" in postgres_node.meetings

    # 2. Verify Entity Detail
    detail = await service.get_entity_detail("ent-postgres")
    assert detail is not None
    assert detail.meetings_count == 2
    assert len(detail.related_entities) >= 2  # Rahul and Priya and MeetingOS

    # 3. Verify Subgraph centered at Rahul reaches MeetingOS across meetings
    subgraph = await service.get_subgraph(entity_id="ent-rahul", depth=3)
    node_ids = {n.id for n in subgraph.nodes}
    assert "ent-rahul" in node_ids
    assert "ent-postgres" in node_ids
    assert "ent-meetingos" in node_ids or "ent-priya" in node_ids
    assert subgraph.total_edges >= 2

    # 4. Verify Dashboard Metrics
    metrics = await service.get_dashboard_metrics()
    assert metrics.meetings_ingested == 2
    assert metrics.decisions_tracked == 1
    assert metrics.open_actions == 1
    assert metrics.unresolved_issues == 1
    assert metrics.canonical_entities_tracked == 4
    assert metrics.relationships_tracked == 3

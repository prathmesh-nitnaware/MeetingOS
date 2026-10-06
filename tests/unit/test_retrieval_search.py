from datetime import UTC, datetime

import pytest
from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    IssueStatus,
    SourceType,
)
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedIssue,
    Meeting,
    TranscriptSegment,
)
from packages.memory.repository import MeetingRepository
from packages.nlp.pipeline import NLPExtractionResult
from packages.retrieval.search import HybridSearchEngine, cosine_similarity


def test_cosine_similarity_basic():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0

    assert cosine_similarity([], []) == 0.0


@pytest.mark.asyncio
async def test_hybrid_search_across_meetings(test_repository: MeetingRepository):
    # Setup 2 meetings
    dt1 = datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC)
    dt2 = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)

    m1 = Meeting(
        meeting_id="meet-search-001",
        title="Architecture Decision Meeting",
        meeting_date=dt1,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="seg-101",
                sequence=0,
                speaker_id="spk_rahul",
                start_time=0.0,
                end_time=5.0,
                text="Rahul: We decided to adopt PostgreSQL and pgvector.",
            )
        ],
    )
    await test_repository.create_meeting(m1)
    await test_repository.save_embeddings(
        "meet-search-001",
        [
            (
                "segment",
                "seg-101",
                "Rahul: We decided to adopt PostgreSQL and pgvector.",
                [0.8, 0.2, 0.1],
            )
        ],
    )
    await test_repository.save_nlp_extraction_results(
        "meet-search-001",
        NLPExtractionResult(
            meeting_id="meet-search-001",
            entities=[
                ExtractedEntity(
                    entity_id="ent-postgres", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
                )
            ],
            decisions=[
                ExtractedDecision(
                    decision_id="dec-101",
                    subject="Adopt PostgreSQL",
                    status=DecisionStatus.APPROVED,
                    meeting_id="meet-search-001",
                )
            ],
        ),
    )

    m2 = Meeting(
        meeting_id="meet-search-002",
        title="Cache and Performance Sync",
        meeting_date=dt2,
        source_type=SourceType.AUDIO_WAV,
        segments=[
            TranscriptSegment(
                segment_id="seg-201",
                sequence=0,
                speaker_id="spk_alex",
                start_time=0.0,
                end_time=5.0,
                text="Alex: We are seeing timeout issues in Redis cluster.",
            )
        ],
    )
    await test_repository.create_meeting(m2)
    await test_repository.save_embeddings(
        "meet-search-002",
        [
            (
                "segment",
                "seg-201",
                "Alex: We are seeing timeout issues in Redis cluster.",
                [0.1, 0.9, 0.2],
            )
        ],
    )
    await test_repository.save_nlp_extraction_results(
        "meet-search-002",
        NLPExtractionResult(
            meeting_id="meet-search-002",
            entities=[
                ExtractedEntity(
                    entity_id="ent-redis", name="Redis", entity_type=EntityType.TECHNOLOGY
                )
            ],
            issues=[
                ExtractedIssue(
                    issue_id="iss-201",
                    description="Redis timeout issues",
                    owner_id="spk_alex",
                    status=IssueStatus.DETECTED,
                    first_detected_at=dt2,
                )
            ],
            commitments=[
                ExtractedCommitment(
                    commitment_id="com-201",
                    description="Investigate Redis timeouts",
                    owner_id="spk_alex",
                    status=CommitmentStatus.ASSIGNED,
                    meeting_id="meet-search-002",
                )
            ],
        ),
    )

    engine = HybridSearchEngine(test_repository.session)

    # 1. Search PostgreSQL
    res1 = await engine.search("PostgreSQL")
    assert res1.total_results >= 1
    assert any("PostgreSQL" in r.text for r in res1.results)
    assert res1.results[0].meeting_id == "meet-search-001"

    # 2. Search Redis with filter
    res2 = await engine.search("Redis", result_type="issue")
    assert res2.total_results >= 1
    assert res2.results[0].source_type == "issue"
    assert "Redis timeout" in res2.results[0].text

    # 3. Search with person filter
    res3 = await engine.search("", person="alex", result_type="action")
    assert res3.total_results >= 1
    assert "Investigate Redis" in res3.results[0].text

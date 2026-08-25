from datetime import UTC, datetime

import pytest
from packages.common.models import TranscriptSegment
from packages.nlp.pipeline import NLPExtractionPipeline


@pytest.mark.asyncio
async def test_nlp_extraction_pipeline_end_to_end():
    pipeline = NLPExtractionPipeline()
    segments = [
        TranscriptSegment(
            segment_id="seg-1",
            sequence=0,
            speaker_id="spk_rahul",
            start_time=0.0,
            end_time=5.0,
            text="Rahul Verma: We decided to adopt PostgreSQL and pgvector for MeetingOS.",
        ),
        TranscriptSegment(
            segment_id="seg-2",
            sequence=1,
            speaker_id="spk_priya",
            start_time=5.5,
            end_time=10.0,
            text="Priya Sharma: I will finish the database benchmarks by Friday.",
        ),
        TranscriptSegment(
            segment_id="seg-3",
            sequence=2,
            speaker_id="spk_alex",
            start_time=10.5,
            end_time=15.0,
            text="Alex Rivera: We have a timeout issue in Redis cache.",
        ),
    ]

    meeting_date = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)
    result = await pipeline.process_transcript(
        meeting_id="meet-101",
        segments=segments,
        meeting_date=meeting_date,
    )

    assert result.meeting_id == "meet-101"
    assert len(result.entities) >= 4
    assert len(result.topics) >= 1
    assert len(result.decisions) >= 1
    assert len(result.commitments) >= 1
    assert len(result.issues) >= 1
    assert len(result.events) >= 1
    assert len(result.classifications) == 3
    assert len(result.evidence) == 3

    # Check decision content
    dec = result.decisions[0]
    assert "PostgreSQL" in dec.subject

    # Check commitment content
    com = result.commitments[0]
    assert com.owner_id == "spk_priya"
    assert com.current_deadline is not None

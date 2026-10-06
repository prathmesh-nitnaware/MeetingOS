from datetime import UTC, datetime

import pytest
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import Meeting, SpeakerInfo, TranscriptSegment
from packages.memory.repository import MeetingRepository


@pytest.mark.asyncio
async def test_repository_create_and_get_meeting(
    test_repository: MeetingRepository, minimal_meeting: Meeting
):
    created_row = await test_repository.create_meeting(minimal_meeting)
    assert created_row.id == minimal_meeting.meeting_id

    fetched = await test_repository.get_meeting(minimal_meeting.meeting_id)
    assert fetched is not None
    assert fetched.meeting_id == minimal_meeting.meeting_id
    assert fetched.title == minimal_meeting.title
    assert len(fetched.participants) == 1
    assert len(fetched.segments) == 1
    assert fetched.segments[0].text == "Hello world."


@pytest.mark.asyncio
async def test_repository_list_meetings(
    test_repository: MeetingRepository, minimal_meeting: Meeting
):
    await test_repository.create_meeting(minimal_meeting)

    second_meeting = Meeting(
        meeting_id="meet-test-02",
        title="Second Standup",
        meeting_date=datetime(2026, 8, 26, 10, 0, 0, tzinfo=UTC),
        source_type=SourceType.TEXT_TRANSCRIPT,
    )
    await test_repository.create_meeting(second_meeting)

    meetings = await test_repository.list_meetings(limit=10)
    assert len(meetings) == 2
    # Ordered by date descending
    assert meetings[0].meeting_id == "meet-test-02"
    assert meetings[1].meeting_id == "meet-test-01"


@pytest.mark.asyncio
async def test_repository_save_and_get_transcript_segments(
    test_repository: MeetingRepository, minimal_meeting: Meeting
):
    await test_repository.create_meeting(minimal_meeting)

    new_segments = [
        TranscriptSegment(
            segment_id="s1",
            sequence=0,
            speaker_id="spk_0",
            start_time=0.0,
            end_time=3.0,
            text="First",
        ),
        TranscriptSegment(
            segment_id="s2",
            sequence=1,
            speaker_id="spk_1",
            start_time=3.5,
            end_time=7.0,
            text="Second",
        ),
    ]
    new_speakers = [
        SpeakerInfo(speaker_id="spk_0", name="Speaker 0"),
        SpeakerInfo(speaker_id="spk_1", name="Speaker 1"),
    ]

    await test_repository.save_transcript_segments(
        minimal_meeting.meeting_id, new_segments, new_speakers
    )
    retrieved = await test_repository.get_transcript_segments(minimal_meeting.meeting_id)
    assert len(retrieved) == 2
    assert retrieved[0].sequence == 0
    assert retrieved[1].sequence == 1


@pytest.mark.asyncio
async def test_repository_update_meeting_status(
    test_repository: MeetingRepository, minimal_meeting: Meeting
):
    await test_repository.create_meeting(minimal_meeting)
    await test_repository.update_meeting_status(
        minimal_meeting.meeting_id, ProcessingStatus.SUCCEEDED, duration_seconds=120.0
    )

    fetched = await test_repository.get_meeting(minimal_meeting.meeting_id)
    assert fetched is not None
    assert fetched.processing_status == ProcessingStatus.SUCCEEDED
    assert fetched.duration_seconds == 120.0


@pytest.mark.asyncio
async def test_repository_job_lifecycle(test_repository: MeetingRepository):
    job_id = "job-test-123"
    job = await test_repository.create_job(job_id=job_id, meeting_id="meet-1", stage="init")
    assert job.id == job_id
    assert job.status == str(ProcessingStatus.QUEUED)

    updated = await test_repository.update_job(
        job_id=job_id, status=ProcessingStatus.RUNNING, stage="speech", progress=0.5
    )
    assert updated is not None
    assert updated.status == str(ProcessingStatus.RUNNING)
    assert updated.progress == 0.5

    fetched = await test_repository.get_job(job_id)
    assert fetched is not None
    assert fetched.stage == "speech"

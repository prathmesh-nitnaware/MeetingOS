import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_and_get_meeting_workflow(async_client: AsyncClient):
    # 1. Upload a meeting file
    file_content = b"RIFF" + b"\x00" * 500
    files = {
        "file": ("team_sync.wav", file_content, "audio/wav"),
    }
    data = {
        "title": "Architecture Sync 2026",
        "meeting_date": "2026-08-25T10:00:00Z",
        "participants": '["Rahul Verma", "Priya Sharma"]',
        "async_processing": "false",
    }

    create_res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert create_res.status_code == 201
    create_data = create_res.json()
    assert "meeting_id" in create_data
    assert "job_id" in create_data
    meeting_id = create_data["meeting_id"]
    job_id = create_data["job_id"]

    # 2. Check Job status
    job_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] == "succeeded"
    assert job_data["progress"] == 1.0

    # 3. List Meetings
    list_res = await async_client.get("/api/v1/meetings")
    assert list_res.status_code == 200
    meetings_list = list_res.json()
    assert len(meetings_list) >= 1
    assert any(m["meeting_id"] == meeting_id for m in meetings_list)

    # 4. Get Meeting Detail
    detail_res = await async_client.get(f"/api/v1/meetings/{meeting_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["meeting_id"] == meeting_id
    assert detail_data["title"] == "Architecture Sync 2026"
    assert detail_data["processing_status"] == "succeeded"
    assert len(detail_data["participants"]) == 2
    assert detail_data["segments_count"] == 3

    # 5. Get Transcript Segments
    transcript_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert transcript_res.status_code == 200
    transcript_data = transcript_res.json()
    assert transcript_data["meeting_id"] == meeting_id
    assert transcript_data["segments_count"] == 3
    assert transcript_data["segments"][0]["sequence"] == 0
    assert "MeetingOS" in transcript_data["segments"][0]["text"]


@pytest.mark.asyncio
async def test_upload_srt_file(async_client: AsyncClient):
    srt_content = b"""1
00:00:01,000 --> 00:00:05,000
Priya: Welcome everyone.

2
00:00:06,000 --> 00:00:10,000
Rahul: Let us review the action items.
"""
    files = {
        "file": ("subtitles.srt", srt_content, "application/x-subrip"),
    }
    data = {
        "title": "SRT Ingestion Meeting",
        "meeting_date": "2026-08-25",
        "async_processing": "false",
    }

    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 201
    meeting_id = res.json()["meeting_id"]

    # Verify transcript
    transcript_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert transcript_res.status_code == 200
    data = transcript_res.json()
    assert data["segments_count"] == 2
    assert data["segments"][0]["speaker_id"] == "spk_priya"


@pytest.mark.asyncio
async def test_upload_unsupported_file_extension(async_client: AsyncClient):
    files = {
        "file": ("malicious.exe", b"MZ....", "application/octet-stream"),
    }
    data = {
        "title": "Bad File",
    }
    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_date_format(async_client: AsyncClient):
    files = {
        "file": ("test.wav", b"RIFF" + b"\x00" * 100, "audio/wav"),
    }
    data = {
        "title": "Bad Date Meeting",
        "meeting_date": "not-a-date",
    }
    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 400
    assert "Invalid meeting_date format" in res.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_meeting_and_job(async_client: AsyncClient):
    res_m = await async_client.get("/api/v1/meetings/non-existent-id")
    assert res_m.status_code == 404

    res_t = await async_client.get("/api/v1/meetings/non-existent-id/transcript")
    assert res_t.status_code == 404

    res_j = await async_client.get("/api/v1/jobs/non-existent-job-id")
    assert res_j.status_code == 404

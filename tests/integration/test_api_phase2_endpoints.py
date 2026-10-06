import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_meeting_nlp_extraction_and_subresources(async_client: AsyncClient):
    # 1. Upload a rich meeting file
    srt_content = b"""1
00:00:01,000 --> 00:00:05,000
Rahul Verma: We decided to adopt PostgreSQL and pgvector for MeetingOS.

2
00:00:06,000 --> 00:00:10,000
Priya Sharma: I will finish the database benchmarks by Friday.

3
00:00:11,000 --> 00:00:15,000
Alex Rivera: We hit a timeout issue in Redis cache.
"""
    files = {
        "file": ("tech_architecture_sync.srt", srt_content, "application/x-subrip"),
    }
    data = {
        "title": "Database and Cache Review",
        "meeting_date": "2026-08-25T10:00:00Z",
        "async_processing": "false",
    }

    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 201
    meeting_id = res.json()["meeting_id"]

    # 2. GET /entities
    ent_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/entities")
    assert ent_res.status_code == 200
    entities = ent_res.json()
    assert len(entities) >= 4
    entity_names = {e["name"] for e in entities}
    assert "PostgreSQL" in entity_names
    assert "Redis" in entity_names

    # 3. GET /topics
    top_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/topics")
    assert top_res.status_code == 200
    topics = top_res.json()
    assert len(topics) >= 1

    # 4. GET /decisions
    dec_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/decisions")
    assert dec_res.status_code == 200
    decisions = dec_res.json()
    assert len(decisions) >= 1
    assert "PostgreSQL" in decisions[0]["subject"]
    assert decisions[0]["status"] == "Approved"

    # 5. GET /actions
    act_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/actions")
    assert act_res.status_code == 200
    actions = act_res.json()
    assert len(actions) >= 1
    assert "Friday" in actions[0]["description"] or "benchmarks" in actions[0]["description"]

    # 6. GET /issues
    iss_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/issues")
    assert iss_res.status_code == 200
    issues = iss_res.json()
    assert len(issues) >= 1
    assert "timeout" in issues[0]["description"]

    # 7. GET /timeline
    time_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/timeline")
    assert time_res.status_code == 200
    events = time_res.json()
    assert len(events) >= 1

    # 8. GET /relations
    rel_res = await async_client.get(f"/api/v1/meetings/{meeting_id}/relations")
    assert rel_res.status_code == 200
    relations = rel_res.json()
    assert len(relations) >= 1

    # 9. POST /extract (on-demand re-extraction)
    extract_res = await async_client.post(f"/api/v1/meetings/{meeting_id}/extract")
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["meeting_id"] == meeting_id
    assert extract_data["entities_count"] >= 4
    assert extract_data["decisions_count"] >= 1


@pytest.mark.asyncio
async def test_subresources_404_for_nonexistent_meeting(async_client: AsyncClient):
    endpoints = ["entities", "topics", "decisions", "actions", "issues", "timeline", "relations"]
    for ep in endpoints:
        res = await async_client.get(f"/api/v1/meetings/non-existent-meet/{ep}")
        assert res.status_code == 404

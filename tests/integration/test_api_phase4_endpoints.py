import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_phase4_temporal_and_lifecycle_api_workflow(async_client: AsyncClient):
    # 1. Ingest Meeting 1: Initial decision & commitment
    srt_1 = b"""1
00:00:01,000 --> 00:00:05,000
Rahul Verma: We decided to adopt MongoDB for database storage.

2
00:00:06,000 --> 00:00:10,000
Priya Sharma: I will complete the migration by Friday.
"""
    files1 = {"file": ("meet_m1.srt", srt_1, "application/x-subrip")}
    data1 = {
        "title": "Architecture Sync 1",
        "meeting_date": "2026-08-01T10:00:00Z",
        "async_processing": "false",
    }
    res1 = await async_client.post("/api/v1/meetings", data=data1, files=files1)
    assert res1.status_code == 201
    m1_id = res1.json()["meeting_id"]

    # 2. Ingest Meeting 2: Reversing decision to PostgreSQL and deadline change
    srt_2 = b"""1
00:00:01,000 --> 00:00:05,000
Rahul Verma: We decided to adopt PostgreSQL which replaces MongoDB.

2
00:00:06,000 --> 00:00:10,000
Priya Sharma: We hit a timeout issue in Redis cache.
"""
    files2 = {"file": ("meet_m2.srt", srt_2, "application/x-subrip")}
    data2 = {
        "title": "Architecture Sync 2",
        "meeting_date": "2026-08-15T10:00:00Z",
        "async_processing": "false",
    }
    res2 = await async_client.post("/api/v1/meetings", data=data2, files=files2)
    assert res2.status_code == 201
    m2_id = res2.json()["meeting_id"]

    # 3. GET /api/v1/timeline
    time_res = await async_client.get("/api/v1/timeline")
    assert time_res.status_code == 200
    timeline = time_res.json()
    event_types = {e["event_type"] for e in timeline}
    assert (
        "DECISION_APPROVED" in event_types
        or "DECISION_REVERSED" in event_types
        or "Decision Approved" in event_types
    )

    # 4. POST /api/v1/temporal/reconcile
    rec_res = await async_client.post("/api/v1/temporal/reconcile", json={"meeting_id": m2_id})
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["meeting_id"] == m2_id

    # 5. Fetch decisions from meeting 1 and check history endpoint
    dec1_res = await async_client.get(f"/api/v1/meetings/{m1_id}/decisions")
    assert dec1_res.status_code == 200
    m1_decisions = dec1_res.json()
    assert len(m1_decisions) >= 1
    m1_dec_id = m1_decisions[0]["decision_id"]

    hist_res = await async_client.get(f"/api/v1/decisions/{m1_dec_id}/history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["decision"]["decision_id"] == m1_dec_id
    assert hist_data["meeting_id"] == m1_id

    # 6. Fetch actions from meeting 1 and check commitment history
    act1_res = await async_client.get(f"/api/v1/meetings/{m1_id}/actions")
    assert act1_res.status_code == 200
    m1_actions = act1_res.json()
    assert len(m1_actions) >= 1
    m1_act_id = m1_actions[0]["commitment_id"]

    com_hist_res = await async_client.get(f"/api/v1/commitments/{m1_act_id}/history")
    assert com_hist_res.status_code == 200
    com_data = com_hist_res.json()
    assert com_data["commitment"]["commitment_id"] == m1_act_id

    # 7. Fetch issues from meeting 2 and check issue history
    iss2_res = await async_client.get(f"/api/v1/meetings/{m2_id}/issues")
    assert iss2_res.status_code == 200
    m2_issues = iss2_res.json()
    assert len(m2_issues) >= 1
    m2_iss_id = m2_issues[0]["issue_id"]

    iss_hist_res = await async_client.get(f"/api/v1/issues/{m2_iss_id}/history")
    assert iss_hist_res.status_code == 200
    iss_data = iss_hist_res.json()
    assert iss_data["issue"]["issue_id"] == m2_iss_id

    # 8. GET /api/v1/entities/{id}/timeline
    ent_res = await async_client.get("/api/v1/entities/ent-postgresql/timeline")
    assert ent_res.status_code == 200
    ent_timeline = ent_res.json()
    assert ent_timeline["entity_id"] == "ent-postgresql"


@pytest.mark.asyncio
async def test_temporal_endpoints_404(async_client: AsyncClient):
    res_dec = await async_client.get("/api/v1/decisions/non-existent-dec/history")
    assert res_dec.status_code == 404

    res_com = await async_client.get("/api/v1/commitments/non-existent-com/history")
    assert res_com.status_code == 404

    res_iss = await async_client.get("/api/v1/issues/non-existent-iss/history")
    assert res_iss.status_code == 404

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_phase3_cross_meeting_memory_and_apis(async_client: AsyncClient):
    # 1. Ingest Meeting 1
    srt_1 = b"""1
00:00:01,000 --> 00:00:05,000
Rahul Verma: We decided to adopt PostgreSQL and pgvector for MeetingOS.

2
00:00:06,000 --> 00:00:10,000
Priya Sharma: I will finish the database benchmarks by Friday.
"""
    files1 = {"file": ("meet_01.srt", srt_1, "application/x-subrip")}
    data1 = {
        "title": "Architecture Sync 1",
        "meeting_date": "2026-08-20T10:00:00Z",
        "async_processing": "false",
    }
    res1 = await async_client.post("/api/v1/meetings", data=data1, files=files1)
    assert res1.status_code == 201
    m1_id = res1.json()["meeting_id"]

    # 2. Ingest Meeting 2 (referencing same PostgreSQL technology and Priya)
    srt_2 = b"""1
00:00:01,000 --> 00:00:05,000
Priya Sharma: We found an issue in the connection pool with PostgreSQL.

2
00:00:06,000 --> 00:00:10,000
Alex Rivera: I will optimize the PostgreSQL connection limits.
"""
    files2 = {"file": ("meet_02.srt", srt_2, "application/x-subrip")}
    data2 = {
        "title": "Architecture Sync 2",
        "meeting_date": "2026-08-25T10:00:00Z",
        "async_processing": "false",
    }
    res2 = await async_client.post("/api/v1/meetings", data=data2, files=files2)
    assert res2.status_code == 201
    m2_id = res2.json()["meeting_id"]

    # 3. GET /api/v1/dashboard
    dash_res = await async_client.get("/api/v1/dashboard")
    assert dash_res.status_code == 200
    metrics = dash_res.json()
    assert metrics["meetings_ingested"] >= 2
    assert metrics["decisions_tracked"] >= 1
    assert metrics["open_actions"] >= 1
    assert metrics["canonical_entities_tracked"] >= 3

    # 4. GET /api/v1/entities
    ent_res = await async_client.get("/api/v1/entities")
    assert ent_res.status_code == 200
    entities = ent_res.json()
    assert len(entities) >= 3
    postgres_entity = next((e for e in entities if "Postgre" in e["name"]), None)
    assert postgres_entity is not None
    assert postgres_entity["meeting_count"] >= 2
    assert m1_id in postgres_entity["meetings"]
    assert m2_id in postgres_entity["meetings"]

    # 5. GET /api/v1/entities/{id}
    ent_detail_res = await async_client.get(f"/api/v1/entities/{postgres_entity['id']}")
    assert ent_detail_res.status_code == 200
    ent_detail = ent_detail_res.json()
    assert ent_detail["entity"]["name"] == postgres_entity["name"]
    assert ent_detail["meetings_count"] >= 2

    # 6. GET /api/v1/graph/entities/{id}
    g_res = await async_client.get(f"/api/v1/graph/entities/{postgres_entity['id']}")
    assert g_res.status_code == 200
    g_data = g_res.json()
    assert g_data["entity"]["entity_id"] == postgres_entity["id"]

    # 7. GET /api/v1/graph/subgraph
    sub_res = await async_client.get("/api/v1/graph/subgraph?depth=2")
    assert sub_res.status_code == 200
    subgraph = sub_res.json()
    assert subgraph["total_nodes"] >= 3
    assert subgraph["total_edges"] >= 1

    # 8. GET /api/v1/search
    search_res = await async_client.get("/api/v1/search?q=PostgreSQL")
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_results"] >= 2
    search_meetings = {r["meeting_id"] for r in s_data["results"]}
    assert m1_id in search_meetings
    assert m2_id in search_meetings


@pytest.mark.asyncio
async def test_search_filtering_and_pagination(async_client: AsyncClient):
    res = await async_client.get("/api/v1/search?type=decision")
    assert res.status_code == 200
    data = res.json()
    assert all(r["source_type"] == "decision" for r in data["results"])

    res_404 = await async_client.get("/api/v1/entities/non-existent-entity-12345")
    assert res_404.status_code == 404

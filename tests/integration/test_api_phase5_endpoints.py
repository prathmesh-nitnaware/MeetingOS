import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_phase5_query_intelligence_api(async_client: AsyncClient):
    # 1. Ingest Meeting 1
    srt_content = b"""1
00:00:05,000 --> 00:00:15,000
Rahul Verma: We evaluated MongoDB and PostgreSQL, and decided to adopt PostgreSQL and pgvector for MeetingOS.

2
00:00:16,000 --> 00:00:25,000
Priya Sharma: I will complete the database schema migration by Friday.
"""
    files = {"file": ("tech_db_sync.srt", srt_content, "application/x-subrip")}
    data = {
        "title": "Database Decisions",
        "meeting_date": "2026-08-25T10:00:00Z",
        "async_processing": "false",
    }
    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 201
    meeting_id = res.json()["meeting_id"]

    # 2. Query: "What decisions have we made about the database?"
    q1_payload = {
        "question": "What decisions have we made about the database?",
        "max_evidence_items": 5,
    }
    q1_res = await async_client.post("/api/v1/query", json=q1_payload)
    assert q1_res.status_code == 200
    q1_data = q1_res.json()

    assert "PostgreSQL" in q1_data["answer"]
    assert q1_data["confidence"] >= 0.8
    assert any(e["meeting_id"] == meeting_id for e in q1_data["evidence"])
    assert all(e["start_time"] >= 0.0 for e in q1_data["evidence"])
    assert all(e["end_time"] > e["start_time"] for e in q1_data["evidence"])
    assert q1_data["query_plan"]["type"] == "decision"
    assert len(q1_data["reasoning_path"]) >= 2

    # 3. Query: "What did Priya commit to by Friday?"
    q2_payload = {
        "question": "What did Priya commit to by Friday?",
    }
    q2_res = await async_client.post("/api/v1/query", json=q2_payload)
    assert q2_res.status_code == 200
    q2_data = q2_res.json()
    assert (
        "Priya" in q2_data["answer"]
        or "migration" in q2_data["answer"]
        or "schema" in q2_data["answer"]
    )
    assert q2_data["query_plan"]["person"] == "Priya"
    assert q2_data["query_plan"]["type"] == "action"

    # 4. Query unanswerable question (Faithfulness test)
    q3_payload = {
        "question": "What is our quantum entanglement protocol for orbital satellites?",
    }
    q3_res = await async_client.post("/api/v1/query", json=q3_payload)
    assert q3_res.status_code == 200
    q3_data = q3_res.json()
    assert "does not establish an answer" in q3_data["answer"]
    assert len(q3_data["evidence"]) == 0
    assert q3_data["confidence"] == 0.0


@pytest.mark.asyncio
async def test_query_api_with_plan_override(async_client: AsyncClient):
    payload = {
        "question": "Tell me about our plans",
        "query_plan_override": {
            "person": "Rahul",
            "topic": "Database",
            "type": "decision",
            "entities": ["PostgreSQL"],
            "intent": "qa",
        },
    }
    res = await async_client.post("/api/v1/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["query_plan"]["person"] == "Rahul"
    assert data["query_plan"]["topic"] == "Database"

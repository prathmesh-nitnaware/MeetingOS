import pytest
from httpx import AsyncClient


@pytest.fixture
async def seeded_client_with_meeting(async_client: AsyncClient) -> str:
    """Ingest a meeting directly through the API client so it is present in the client's test DB."""
    srt_content = b"""1
00:00:01,000 --> 00:00:15,000
Rahul Verma: We decided to adopt PostgreSQL as our primary database because of pgvector vector support.

2
00:00:16,000 --> 00:00:30,000
Priya Sharma: Priya Sharma is the owner of this database migration task, due by Friday.
"""
    files = {"file": ("agentic_meeting.srt", srt_content, "application/x-subrip")}
    data = {
        "title": "PostgreSQL Architecture Decision",
        "meeting_date": "2026-08-25T10:00:00Z",
        "async_processing": "false",
    }
    res = await async_client.post("/api/v1/meetings", data=data, files=files)
    assert res.status_code == 201
    return res.json()["meeting_id"]


@pytest.mark.asyncio
async def test_agentic_query_grounded_answer(
    async_client: AsyncClient,
    seeded_client_with_meeting: str,  # noqa: ARG001
):
    """Validate successful grounded answering with confidence and citations."""
    headers = {"Authorization": "Bearer admin-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Why did we adopt PostgreSQL?"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data
    assert data["confidence"] > 0.0
    assert "postgresql" in data["answer"].lower()
    assert len(data["evidence"]) > 0
    assert len(data["citations"]) > 0
    assert len(data["trace"]) > 0
    assert data["insufficient_evidence"] is False


@pytest.mark.asyncio
async def test_agentic_query_insufficient_evidence(
    async_client: AsyncClient,
    seeded_client_with_meeting: str,  # noqa: ARG001
):
    """Validate that ungrounded queries return zero confidence and refusal."""
    headers = {"Authorization": "Bearer admin-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "What did the board decide about Snowflake data warehousing budget?"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    # Must refuse gracefully
    assert (
        data["confidence"] == 0.0
        or "does not establish" in data["answer"].lower()
        or data["insufficient_evidence"] is True
    )


@pytest.mark.asyncio
async def test_agentic_query_trace_and_confidence(
    async_client: AsyncClient,
    seeded_client_with_meeting: str,  # noqa: ARG001
):
    """Verify trace records individual specialist agents."""
    headers = {"Authorization": "Bearer member-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Who owns the database migration task?"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    agents_invoked = [t["agent"] for t in data["trace"]]
    assert "planner" in agents_invoked
    assert "retrieval" in agents_invoked
    assert "evidence" in agents_invoked
    assert "answer" in agents_invoked


@pytest.mark.asyncio
async def test_agentic_query_validation_error(async_client: AsyncClient):
    """Missing question payload should return 422 Unprocessable Entity."""
    headers = {"Authorization": "Bearer admin-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agentic_query_unauthorized(async_client: AsyncClient):
    """Missing or invalid auth token should return 401 Unauthorized."""
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Why PostgreSQL?"},
    )
    assert response.status_code == 401

    invalid_auth = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Why PostgreSQL?"},
        headers={"Authorization": "Bearer invalid-bogus-token"},
    )
    assert invalid_auth.status_code == 401


@pytest.mark.asyncio
async def test_agentic_query_viewer_role_permitted(
    async_client: AsyncClient,
    seeded_client_with_meeting: str,  # noqa: ARG001
):
    """Viewer token must have read access to agentic query endpoint."""
    headers = {"Authorization": "Bearer viewer-secret-token"}
    response = await async_client.post(
        "/api/v1/query/agentic",
        json={"question": "Why did we adopt PostgreSQL?"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_security_protected_endpoints_require_auth(async_client: AsyncClient):
    """Ensure sensitive API surfaces require valid Bearer token."""
    protected_paths = [
        ("GET", "/api/v1/connectors"),
        ("GET", "/api/v1/audit"),
        ("POST", "/api/v1/admin/retention/cleanup"),
        ("POST", "/api/v1/query/agentic"),
    ]
    for method, path in protected_paths:
        if method == "GET":
            resp = await async_client.get(path)
        else:
            resp = await async_client.post(path, json={"question": "test"})
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated {method} {path}, got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_security_connector_credentials_not_leaked(async_client: AsyncClient):
    """Connector configs should never leak secret API keys or credentials in response bodies."""
    headers = {"Authorization": "Bearer admin-secret-token"}
    resp = await async_client.get("/api/v1/connectors", headers=headers)
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "client_secret" not in text
    assert "private_key" not in text

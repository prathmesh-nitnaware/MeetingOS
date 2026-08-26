import pytest
from httpx import AsyncClient
from packages.agents.traces import AgentExecutionTrace, global_trace_store

HEADERS_VIEWER = {"Authorization": "Bearer viewer-secret-token"}
HEADERS_ADMIN = {"Authorization": "Bearer admin-secret-token"}


@pytest.mark.asyncio
async def test_traces_and_metrics_endpoints(async_client: AsyncClient):
    # 1. Seed a trace into global_trace_store
    trace_id = "tr-api-phase12-test"
    global_trace_store.save_trace(
        AgentExecutionTrace(
            trace_id=trace_id,
            query_id="qry-api-phase12-test",
            query="Which database was selected?",
            answer="PostgreSQL with pgvector",
            confidence=0.95,
            citations=["Database Sync (2026-08-20) - 0:00"],
        )
    )

    # 2. Test list traces (200 OK)
    res = await async_client.get("/api/v1/query/traces", headers=HEADERS_VIEWER)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(t["trace_id"] == trace_id for t in data)

    # 3. Test get trace by ID
    res_single = await async_client.get(f"/api/v1/query/traces/{trace_id}", headers=HEADERS_VIEWER)
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["trace_id"] == trace_id
    assert single_data["query"] == "Which database was selected?"

    # 4. Test provider usage metrics
    res_metrics = await async_client.get("/api/v1/admin/metrics/usage", headers=HEADERS_VIEWER)
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert "total_requests" in metrics_data
    assert "avg_latency_ms" in metrics_data
    assert "p50_latency_ms" in metrics_data

    # 5. Test provider status (Zero Secret Leakage)
    res_status = await async_client.get("/api/v1/admin/providers/status", headers=HEADERS_VIEWER)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "embedding_provider" in status_data
    assert "reasoner_provider" in status_data
    assert "api_key" not in status_data
    assert "secret" not in str(status_data)

    # 6. Test 401 Unauthorized
    res_unauth = await async_client.get("/api/v1/query/traces")
    assert res_unauth.status_code == 401

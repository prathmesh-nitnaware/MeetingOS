import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_contract_health(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded", "ok")
    assert "version" in data
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_api_contract_dashboard(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "meetings_ingested" in data
    assert "decisions_tracked" in data


@pytest.mark.asyncio
async def test_api_contract_provider_status(async_client: AsyncClient):
    headers = {"Authorization": "Bearer admin-secret-token"}
    resp = await async_client.get("/api/v1/admin/providers/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "embedding_provider" in data
    assert "reasoner_provider" in data


@pytest.mark.asyncio
async def test_api_contract_root_redirect(async_client: AsyncClient):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "docs" in data
    assert "health" in data


@pytest.mark.asyncio
async def test_api_contract_not_found(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/non_existent_route_404")
    assert resp.status_code == 404

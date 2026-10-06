import pytest
from apps.api.config import settings
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "MeetingOS" in data["message"]
    assert "/api/v1/health" in data["health"]


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["app_name"] == "MeetingOS API"
    assert data["version"] == settings.app_version
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "redis" in data["dependencies"]
    # The public health probe must not leak internals or tenant data
    assert "python_version" not in data
    assert "details" not in data


@pytest.mark.asyncio
async def test_openapi_docs_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "MeetingOS API"

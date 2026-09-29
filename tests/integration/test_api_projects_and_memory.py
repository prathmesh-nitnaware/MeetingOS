from datetime import UTC, datetime
from pathlib import Path

import pytest
from apps.api.config import settings
from apps.api.main import create_app
from httpx import ASGITransport, AsyncClient
from packages.memory.models import Base
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer admin-secret-token"}


@pytest.fixture
def org_b_headers():
    return {"Authorization": "Bearer admin-beta-token"}


@pytest.mark.asyncio
async def test_projects_api_flow(tmp_path: Path, auth_headers, org_b_headers):
    """Test full Projects API flow and isolation via HTTP requests."""
    db_file = tmp_path / "test_api_proj.db"
    settings.database_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create project in org_dev
        res = await client.post(
            "/api/v1/projects",
            json={"name": "Q4 Release", "description": "Q4 production readiness", "color": "#10b981"},
            headers=auth_headers,
        )
        assert res.status_code == 201
        proj_data = res.json()
        proj_id = proj_data["id"]

        # 2. List projects in org_dev
        res = await client.get("/api/v1/projects", headers=auth_headers)
        assert res.status_code == 200
        projs = res.json()
        assert len(projs) >= 1
        assert any(p["id"] == proj_id for p in projs)

        # 3. Org B should NOT see org_dev project
        res = await client.get("/api/v1/projects", headers=org_b_headers)
        assert res.status_code == 200
        assert not any(p["id"] == proj_id for p in res.json())

        # 4. Org B cannot access org_dev project detail directly
        res = await client.get(f"/api/v1/projects/{proj_id}", headers=org_b_headers)
        assert res.status_code == 404

        # 5. Create text meeting linked to project
        res = await client.post(
            "/api/v1/meetings/create-text",
            json={
                "title": "Release Go/No-Go",
                "content": "Alex: We approved the production release for Friday.\nDavid: I will monitor the deployment pipeline by Friday.",
                "project_id": proj_id,
                "auto_analyze": True,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        m_id = res.json()["meeting_id"]

        # 6. Verify project meetings and timeline
        res = await client.get(f"/api/v1/projects/{proj_id}/meetings", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

        res = await client.get(f"/api/v1/projects/{proj_id}/timeline", headers=auth_headers)
        assert res.status_code == 200
        timeline = res.json()
        assert len(timeline) >= 1
        assert timeline[0]["meeting_id"] == m_id

        # 7. Test Meeting Evidence API
        res = await client.get(f"/api/v1/meetings/{m_id}/evidence", headers=auth_headers)
        assert res.status_code == 200
        ev_data = res.json()
        assert len(ev_data["decisions_evidence"]) >= 1
        assert len(ev_data["actions_evidence"]) >= 1

        # 8. Test Review status update
        dec_id = ev_data["decisions_evidence"][0]["decision_id"]
        res = await client.patch(
            f"/api/v1/meetings/{m_id}/decisions/{dec_id}/review?review_status=confirmed",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["review_status"] == "confirmed"

        # 9. Test Activity Feed API
        res = await client.get("/api/v1/dashboard/activity", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

        # 10. Test Topic Detail API
        res = await client.get("/api/v1/knowledge/topics/Release", headers=auth_headers)
        assert res.status_code == 200
        topic_detail = res.json()
        assert topic_detail["meeting_count"] >= 1

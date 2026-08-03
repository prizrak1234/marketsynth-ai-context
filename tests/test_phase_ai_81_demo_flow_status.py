"""Phase AI.81 — Demo flow status endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.e2e_demo_seed_service import E2eDemoSeedService


@pytest.mark.asyncio
async def test_demo_flow_status_after_seed(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    from uuid import UUID

    bootstrap = client.post("/projects", json={"name": "AI.81 bootstrap"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    result = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    response = client.get(
        f"/projects/{result.project_id}/demo-flow/status",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["marketing_plan_status"] == "approved"
    assert body["content_asset_status"] == "approved"
    assert body["publication_package_status"] == "approved"
    assert body["publication_job_status"] == "queued"
    assert "payload_snapshot" not in str(body)
    assert "bot_token" not in str(body).lower()


def test_demo_flow_status_hidden_when_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_FLOW_ENDPOINTS_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.81 hidden"}, headers=auth_headers).json()[
        "id"
    ]
    response = client.get(
        f"/projects/{project_id}/demo-flow/status",
        headers=auth_headers,
    )
    assert response.status_code == 404
    get_settings.cache_clear()

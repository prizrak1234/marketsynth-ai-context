"""Phase AI.74 — Telegram publish audit and metrics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from app.db.repositories.publishing_audit_events import PublishingAuditEventRepository
from app.publishing_foundation.contracts import PublishingAuditEventType
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


@patch("app.publishing.providers.telegram_provider.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_audit_and_metrics_after_real_execute(
    mock_client_cls: object,
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "audit-token")
    get_settings.cache_clear()

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 7}}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    project_id = client.post("/projects", json={"name": "AI.74"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    events = await PublishingAuditEventRepository(db_session).list_by_project(
        UUID(project["owner_id"]),
        UUID(project_id),
        limit=20,
    )
    types = {e.event_type for e in events}
    assert PublishingAuditEventType.JOB_REAL_EXECUTE_REQUESTED in types
    assert PublishingAuditEventType.JOB_SUCCEEDED in types
    for event in events:
        blob = str(event.safe_metadata)
        assert "audit-token" not in blob
        assert "bot_token" not in blob

    metrics = client.get(
        f"/projects/{project_id}/publishing-foundation/metrics",
        headers=auth_headers,
    ).json()
    assert metrics["real_jobs_succeeded"] >= 1
    assert metrics["jobs_by_provider"].get("telegram", 0) >= 1

"""Phase AI.72 — Telegram adapter gated execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


def test_telegram_execute_disabled_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "false")
    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.72 off"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["error_code"] in (
        "telegram_unavailable",
        "telegram_auth_failed",
    )


@patch("app.publishing.providers.telegram_provider.httpx.AsyncClient")
def test_telegram_execute_success_safe_metadata(
    mock_client_cls: object,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-12345")
    get_settings.cache_clear()

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 42, "chat": {"id": -1001234567890}},
    }
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    project_id = client.post("/projects", json={"name": "AI.72 ok"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    meta = body["result_metadata"]
    assert meta["provider"] == "telegram"
    assert meta["message_id"] == 42
    assert "test-token" not in str(body)
    assert mock_resp.json.return_value["result"] not in meta.values()

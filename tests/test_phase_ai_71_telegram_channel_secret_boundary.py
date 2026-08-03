"""Phase AI.71 — Telegram channel secret boundary."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient

def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.71"}, headers=headers).json()["id"]


def test_token_in_config_metadata_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/publishing-foundation/channels",
        json={
            "name": "Bad TG",
            "channel_type": "telegram",
            "status": "active",
            "config_metadata": {"chat_id": "-1001", "bot_token": "secret"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_missing_bot_token_blocks_execute(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.publishing_workflow import (
        active_foundation_channel_id,
        approved_publication_package_id,
    )

    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_PUBLICATION_BOT_TOKEN", raising=False)
    get_settings.cache_clear()

    project_id = _project_id(client, auth_headers)
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
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["error_code"] == "telegram_auth_failed"

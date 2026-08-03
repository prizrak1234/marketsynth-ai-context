"""Phase AI.75 — Telegram publishing freeze invariants."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


def test_feature_flag_off_blocks_telegram_execute(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "false")
    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.75"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    result = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )
    assert result.json()["status"] == "failed"


@patch("app.publishing.providers.telegram_provider.httpx.AsyncClient")
def test_idempotency_and_dry_run_still_work(
    mock_client_cls: object,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.publishing_foundation.contracts import PublicationPackageJobStatus

    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "freeze-token")
    get_settings.cache_clear()

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    project_id = client.post(
        "/projects",
        json={"name": "AI.75 stack"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    headers = {**auth_headers, "Idempotency-Key": "tg-freeze-1"}

    first = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    second = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    assert second.json()["id"] == first.json()["id"]

    dry = client.post(
        f"/projects/{project_id}/publication-package-jobs/{first.json()['id']}/execute-dry-run",
        headers=auth_headers,
    )
    assert dry.json()["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value

    second_job = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers={**auth_headers, "Idempotency-Key": "tg-freeze-2"},
    )
    assert second_job.status_code == 201
    real = client.post(
        f"/projects/{project_id}/publication-package-jobs/{second_job.json()['id']}/execute",
        headers=auth_headers,
    )
    assert real.json()["status"] == "succeeded"

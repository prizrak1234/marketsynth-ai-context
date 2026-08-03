"""Phase AI.73 — Real publish endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


@patch("app.publishing.providers.telegram_provider.httpx.AsyncClient")
def test_execute_instagram_channel_blocked(
    _mock_http: object,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.73"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(
        client,
        auth_headers,
        project_id,
        channel="instagram",
    )
    channel_id = active_foundation_channel_id(
        client,
        auth_headers,
        project_id,
        channel_type="instagram",
    )
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "not enabled" in response.json()["detail"].lower()


@patch("app.publishing.providers.telegram_provider.httpx.AsyncClient")
def test_dry_run_unchanged_after_execute_added(
    mock_client_cls: object,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.73 dry"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    dry = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert dry.status_code == 200
    assert dry.json()["status"] == "dry_run_succeeded"
    mock_client_cls.assert_not_called()

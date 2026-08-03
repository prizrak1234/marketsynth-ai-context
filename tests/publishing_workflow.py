"""Helpers for publishing foundation/reliability tests (AI.60–AI.69)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def approved_publication_package_id(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    channel: str = "telegram",
) -> str:
    asset_id = _approved_asset_id(client, headers, project_id)
    package_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": channel},
        headers=headers,
    ).json()["publication_package_id"]
    client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/approve",
        headers=headers,
    )
    return package_id


def _approved_asset_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    created = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "telegram_post", "title": "Pub", "body": "Body"},
        headers=headers,
    )
    asset_id = created.json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    return asset_id


def active_foundation_channel_id(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    channel_type: str = "telegram",
    config_metadata: dict | None = None,
) -> str:
    if config_metadata is None:
        config_metadata = (
            {"chat_id": "-1001234567890"}
            if channel_type == "telegram"
            else {"locale": "ru"}
        )
    response = client.post(
        f"/projects/{project_id}/publishing-foundation/channels",
        json={
            "name": f"Channel {channel_type}",
            "channel_type": channel_type,
            "status": "active",
            "config_metadata": config_metadata,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def queued_publication_package_job_id(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    channel_type: str = "telegram",
) -> str:
    package_id = approved_publication_package_id(
        client,
        headers,
        project_id,
        channel=channel_type,
    )
    channel_id = active_foundation_channel_id(
        client,
        headers,
        project_id,
        channel_type=channel_type,
    )
    response = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]

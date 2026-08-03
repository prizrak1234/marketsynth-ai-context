"""Shared HTTP helpers for media production workflow (Phase AI.50+)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.content_asset_workflow import approve_content_asset


def approved_content_asset_id(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Media source post",
    body: str = "Post body for visual brief",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "telegram_post", "title": title, "body": body},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    asset_id = response.json()["id"]
    approve_content_asset(client, headers, project_id, asset_id)
    return asset_id


def approve_media_brief(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    brief_id: str,
) -> None:
    submitted = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/submit-review",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text

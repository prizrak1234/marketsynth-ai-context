"""Shared HTTP helpers for content asset review workflow (Phase AI.42+)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def submit_content_asset_for_review(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
):
    return client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )


def approve_content_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
):
    """Submit for review then approve — canonical human workflow."""
    submitted = submit_content_asset_for_review(client, headers, project_id, asset_id)
    assert submitted.status_code == 200, submitted.text
    return client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )

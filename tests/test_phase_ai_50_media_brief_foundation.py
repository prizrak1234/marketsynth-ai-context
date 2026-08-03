"""Phase AI.50 — MediaBrief foundation (no generation)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "AI.50 MediaBrief"},
        headers=headers,
    ).json()["id"]


def test_list_media_briefs_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/media-briefs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []

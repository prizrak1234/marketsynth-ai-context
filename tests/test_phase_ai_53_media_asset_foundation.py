"""Phase AI.53 — MediaAsset foundation (placeholder, no generation)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.media_workflow import approved_content_asset_id, approve_media_brief


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.53 MediaAsset"}, headers=headers).json()["id"]


def _approved_brief(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = approved_content_asset_id(client, headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, headers, project_id, brief_id)
    return brief_id


def test_list_media_assets_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/media-assets",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_placeholder_supports_media_types(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = _approved_brief(client, auth_headers, project_id)

    for media_type in ("image", "video", "carousel"):
        response = client.post(
            f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
            json={"media_type": media_type},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["media_type"] == media_type

    listed = client.get(
        f"/projects/{project_id}/media-assets",
        params={"media_brief_id": brief_id},
        headers=auth_headers,
    ).json()
    assert len(listed) == 3

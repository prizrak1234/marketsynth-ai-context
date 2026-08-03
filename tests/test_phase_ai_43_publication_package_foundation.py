"""Phase AI.43 — PublicationPackage foundation (no send)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "AI.43 Packages"},
        headers=headers,
    ).json()["id"]


def _approved_asset_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    created = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "telegram_post", "title": "Post", "body": "Hello"},
        headers=headers,
    )
    assert created.status_code == 201
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


def test_list_publication_packages_empty(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/publication-packages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_package_supports_all_channels(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approved_asset_id(client, auth_headers, project_id)

    for channel in ("telegram", "instagram", "linkedin", "blog"):
        response = client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
            json={"channel": channel},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["channel"] == channel
        assert body["publication_package_status"] == "draft"

    listed = client.get(
        f"/projects/{project_id}/publication-packages",
        params={"content_asset_id": asset_id},
        headers=auth_headers,
    ).json()
    assert len(listed) == 4
    channels = {row["channel"] for row in listed}
    assert channels == {"telegram", "instagram", "linkedin", "blog"}


def test_get_publication_package(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approved_asset_id(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "blog", "cta": "Read more"},
        headers=auth_headers,
    ).json()

    detail = client.get(
        f"/projects/{project_id}/publication-packages/{created['publication_package_id']}",
        headers=auth_headers,
    ).json()
    assert detail["status"] == "draft"
    assert detail["source_content_asset_id"] == asset_id
    assert detail["content_asset_id"] == asset_id
    assert detail["cta"] == "Read more"

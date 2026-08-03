"""Phase UI.9 — manual HTTP revisions for draft content assets."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Manual revisions"},
        headers=headers,
    ).json()["id"]


def _create_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Draft title",
    body: str = "Initial body",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "telegram_post", "title": title, "body": body},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _manual_revision(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
    payload: dict,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/revisions",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_draft_manual_revision_creates_new_version(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)

    updated = _manual_revision(
        client,
        auth_headers,
        project_id,
        asset_id,
        {
            "title": "Revised title",
            "body": "Revised body",
            "metadata_patch": {"editor": "human"},
        },
    )
    assert updated["id"] == asset_id
    assert updated["status"] == "draft"
    assert updated["title"] == "Revised title"
    assert updated["body"] == "Revised body"
    assert updated["current_version_number"] == 2
    assert updated["approved_version_number"] is None
    assert updated["metadata"].get("editor") == "human"

    versions = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions",
        headers=auth_headers,
    ).json()
    assert len(versions) == 2
    assert versions[1]["body"] == "Revised body"


def test_approved_asset_rejects_manual_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/revisions",
        json={"title": "Nope", "body": "Nope", "metadata_patch": {}},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_asset_rejects_manual_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/revisions",
        json={"title": "Nope", "body": "Nope", "metadata_patch": {}},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_manual_revision_does_not_auto_approve(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)

    updated = _manual_revision(
        client,
        auth_headers,
        project_id,
        asset_id,
        {"title": "Still draft", "body": "Still draft body", "metadata_patch": {}},
    )
    assert updated["status"] == "draft"
    assert updated["approved_version_number"] is None

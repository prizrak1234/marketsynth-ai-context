"""Phase AI.61 — PublicationPackage approval gate."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.publishing_workflow import _approved_asset_id


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.61"}, headers=headers).json()["id"]


def _draft_package_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = _approved_asset_id(client, headers, project_id)
    return client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=headers,
    ).json()["publication_package_id"]


def test_review_workflow_transitions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    package_id = _draft_package_id(client, auth_headers, project_id)

    submit = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/submit-review",
        headers=auth_headers,
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "review"
    assert submit.json()["submitted_for_review_at"] is not None

    approve = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["approved_at"] is not None


def test_draft_cannot_skip_to_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    package_id = _draft_package_id(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_is_terminal(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    package_id = _draft_package_id(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/archive",
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409

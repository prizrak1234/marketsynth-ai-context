"""Projects API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_projects_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_resp = client.post(
        "/projects",
        json={"name": "Demo", "description": "test"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    project = create_resp.json()
    project_id = project["id"]

    assert client.get(f"/projects/{project_id}", headers=auth_headers).status_code == 200

    filtered = client.get("/projects", headers=auth_headers)
    assert filtered.status_code == 200
    assert any(p["id"] == project_id for p in filtered.json())

    patch_resp = client.patch(
        f"/projects/{project_id}",
        json={"name": "Renamed"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed"

    assert client.delete(f"/projects/{project_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/projects/{project_id}", headers=auth_headers).status_code == 404


def test_projects_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(f"/projects/{uuid4()}", headers=auth_headers).status_code == 404


def test_projects_require_auth(client: TestClient) -> None:
    assert client.get("/projects").status_code == 401

"""Tasks API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_tasks_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "P"},
        headers=auth_headers,
    ).json()["id"]

    create_resp = client.post(
        "/tasks",
        json={"project_id": project_id, "title": "Do work", "status": "pending"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    task = create_resp.json()
    task_id = task["id"]

    assert client.get(f"/tasks/{task_id}", headers=auth_headers).status_code == 200

    listed = client.get("/tasks", params={"project_id": project_id}, headers=auth_headers)
    assert listed.status_code == 200
    assert any(t["id"] == task_id for t in listed.json())

    patch_resp = client.patch(
        f"/tasks/{task_id}",
        json={"status": "completed", "output_payload": {"ok": True}},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"

    assert client.delete(f"/tasks/{task_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{task_id}", headers=auth_headers).status_code == 404


def test_tasks_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(f"/tasks/{uuid4()}", headers=auth_headers).status_code == 404

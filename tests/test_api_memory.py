"""Memory API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_memory_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Mem project"},
        headers=auth_headers,
    ).json()["id"]

    create_resp = client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "session:1",
            "content": "hello",
            "metadata": {"source": "test"},
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    memory_id = item["id"]
    assert item["metadata"] == {"source": "test"}

    assert client.get(f"/memory/{memory_id}", headers=auth_headers).status_code == 200

    listed = client.get(
        "/memory",
        params={"project_id": project_id},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert any(m["id"] == memory_id for m in listed.json())

    patch_resp = client.patch(
        f"/memory/{memory_id}",
        json={"content": "updated", "metadata": {"source": "patch"}},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["content"] == "updated"

    assert client.delete(f"/memory/{memory_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/memory/{memory_id}", headers=auth_headers).status_code == 404


def test_memory_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(f"/memory/{uuid4()}", headers=auth_headers).status_code == 404


def test_memory_list_by_agent_id_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert (
        client.get("/memory", params={"agent_id": str(uuid4())}, headers=auth_headers).json()
        == []
    )

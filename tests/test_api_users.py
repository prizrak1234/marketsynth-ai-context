"""Users API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_users_crud(client: TestClient) -> None:
    create_resp = client.post(
        "/users",
        json={"telegram_id": 42, "email": "u@example.com", "display_name": "Alice"},
    )
    assert create_resp.status_code == 201
    user = create_resp.json()
    user_id = user["id"]
    assert user["telegram_id"] == 42

    get_resp = client.get(f"/users/{user_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["display_name"] == "Alice"

    list_resp = client.get("/users")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    patch_resp = client.patch(f"/users/{user_id}", json={"display_name": "Bob"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["display_name"] == "Bob"

    delete_resp = client.delete(f"/users/{user_id}")
    assert delete_resp.status_code == 204

    assert client.get(f"/users/{user_id}").status_code == 404


def test_users_get_not_found(client: TestClient) -> None:
    assert client.get(f"/users/{uuid4()}").status_code == 404

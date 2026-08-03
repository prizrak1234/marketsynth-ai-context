"""Health and version endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok_with_db_and_redis(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "ok"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"


def test_version_returns_metadata(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "botfazer"
    assert "version" in data
    assert data["environment"] == "development"

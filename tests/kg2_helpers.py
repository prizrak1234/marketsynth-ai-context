"""Shared helpers for KG.2 governed knowledge in API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def publish_drilling_governed_knowledge(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    code: str = "test.drilling.governed",
) -> dict[str, str]:
    """Candidate → owner → validate → publish for industrial domain tests."""
    project = client.post(
        "/projects",
        headers=auth_headers,
        json={"name": "KG seed", "description": "seed"},
    )
    assert project.status_code in {200, 201}, project.text
    owner_id = client.get(
        f"/projects/{project.json()['id']}", headers=auth_headers
    ).json()["owner_id"]

    created = client.post(
        "/knowledge-governance/candidates",
        headers=auth_headers,
        json={
            "code": code,
            "title": "Слабые сигналы на буровой",
            "content": (
                "# Слабые сигналы\n"
                "Фиксация near miss и слабых сигналов обязательна до инцидента.\n"
                "# Супервайзер\n"
                "Буровой супервайзер отвечает за своевременную эскалацию.\n"
            ),
            "source_uri": "canonical://drilling/weak-signals",
            "domain": "operations",
        },
    )
    assert created.status_code == 201, created.text
    object_id = created.json()["object_id"]
    version_id = created.json()["version_id"]
    assert (
        client.post(
            f"/knowledge-governance/objects/{object_id}/assign-owner",
            headers=auth_headers,
            json={"owner_user_id": owner_id, "reviewer_user_id": owner_id},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/knowledge-governance/versions/{version_id}/validate",
            headers=auth_headers,
            json={"decision": "approve", "next_review_days": 90},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/knowledge-governance/versions/{version_id}/publish",
            headers=auth_headers,
            json={},
        ).status_code
        == 200
    )
    return {"object_id": object_id, "version_id": version_id, "owner_id": owner_id}

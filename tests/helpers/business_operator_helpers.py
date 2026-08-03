"""Shared helpers for business operator API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def analyze_operator(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    message: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": message},
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()


def complete_and_confirm_brief(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    assist_body: dict,
    *,
    extra_answers: dict[str, str] | None = None,
) -> str:
    answers = {
        "offer": "Premium service packages for local customers",
        "target_audience": "Local adults looking for trusted providers",
        **(extra_answers or {}),
    }
    completed = client.post(
        f"/projects/{project_id}/business-operator/brief/complete",
        json={
            "intent": assist_body["intent"],
            "recommended_scenario": assist_body["recommended_scenario"],
            "brief": assist_body["brief_draft"],
            "answers": answers,
        },
        headers=auth_headers,
    )
    assert completed.status_code == 200
    brief_draft = completed.json()["brief_draft"]
    confirmed = client.post(
        f"/projects/{project_id}/business-operator/brief/confirm",
        json={
            "intent": assist_body["intent"],
            "recommended_scenario": assist_body["recommended_scenario"],
            "brief": brief_draft,
        },
        headers=auth_headers,
    )
    assert confirmed.status_code == 200
    return confirmed.json()["brief"]["id"]


def create_operator_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    assist_body: dict,
    brief_id: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"intent": assist_body["intent"], "brief_id": brief_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()

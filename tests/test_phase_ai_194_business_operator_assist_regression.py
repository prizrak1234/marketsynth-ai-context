"""Phase AI.194 — Business Operator assist mode regression."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


def test_dental_high_confidence_passes_gate_with_preview(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.194 dental gate")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "Мне нужны лиды для стоматологии"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence_gate_passed"] is True
    assert body["confidence_threshold"] == 0.65
    assert body["intent"]["confidence"] >= 0.65
    assert body["recommended_scenario"] == "dental_clinic_lead_gen"
    assert not body["clarification_questions"]
    assert body["explanation"] is not None
    assert body["explanation"]["why_this_scenario"]
    assert body["explanation"]["what_will_be_created"]
    assert body["explanation"]["what_user_must_confirm"]
    assert body["preview"] is not None
    assert body["preview"]["specialists_count"] > 0
    assert body["preview"]["expected_artifacts"]
    assert body["intent_audit_id"]
    assert len(body["message_preview"]) <= 80


def test_vague_message_returns_clarification_not_preview(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.194 vague")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence_gate_passed"] is False
    assert body["intent"]["confidence"] < 0.65
    assert body["clarification_questions"]
    assert any(q["missing_field"] == "industry" for q in body["clarification_questions"])
    assert body["preview"] is None
    assert body["explanation"] is None


def test_clarify_answers_improve_confidence_and_unlock_preview(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.194 clarify")
    analyzed = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    ).json()
    clarified = client.post(
        f"/projects/{project_id}/business-operator/clarify",
        json={
            "previous_intent": analyzed["intent"],
            "answers": {"industry": "dental"},
        },
        headers=auth_headers,
    )
    assert clarified.status_code == 200
    body = clarified.json()
    assert body["confidence_gate_passed"] is True
    assert body["intent"]["industry"] == "dental"
    assert body["intent"]["confidence"] >= 0.65
    assert body["recommended_scenario"] == "dental_clinic_lead_gen"
    assert body["preview"] is not None
    assert body["explanation"] is not None


def test_create_blocked_before_confidence_gate(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from uuid import uuid4

    project_id = create_project(client, auth_headers, "AI.194 gate block")
    analyzed = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    ).json()
    blocked = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"message": "хочу клиентов", "brief_id": str(uuid4())},
        headers=auth_headers,
    )
    assert blocked.status_code == 409

    blocked_intent = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"intent": analyzed["intent"], "brief_id": str(uuid4())},
        headers=auth_headers,
    )
    assert blocked_intent.status_code == 409


def test_analyze_does_not_create_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.194 no auto create")
    before = client.get(
        f"/projects/{project_id}/business-campaigns",
        headers=auth_headers,
    )
    assert before.status_code == 200
    count_before = len(before.json())

    analyze = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "Мне нужны лиды для стоматологии"},
        headers=auth_headers,
    )
    assert analyze.status_code == 200

    after = client.get(
        f"/projects/{project_id}/business-campaigns",
        headers=auth_headers,
    )
    assert len(after.json()) == count_before


def test_alternatives_returned_in_recommendation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.194 alternatives")
    body = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "Мне нужны лиды для стоматологии"},
        headers=auth_headers,
    ).json()
    assert body["recommendation"]["alternative_scenarios"]
    assert body["explanation"]["alternatives"]


def test_create_after_clarify_with_confirmed_intent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from tests.helpers.business_operator_helpers import complete_and_confirm_brief

    project_id = create_project(client, auth_headers, "AI.194 create after clarify")
    analyzed = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    ).json()
    clarified = client.post(
        f"/projects/{project_id}/business-operator/clarify",
        json={
            "previous_intent": analyzed["intent"],
            "answers": {"industry": "dental"},
        },
        headers=auth_headers,
    ).json()
    brief_id = complete_and_confirm_brief(
        client,
        auth_headers,
        project_id,
        clarified,
        extra_answers={
            "offer": "Dental implants and hygiene packages",
            "target_audience": "Adults 30-55 in the city",
        },
    )
    created = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"intent": clarified["intent"], "brief_id": brief_id},
        headers=auth_headers,
    )
    assert created.status_code == 201
    campaign = created.json()["campaign"]
    assert campaign["scenario_id"] == "dental_clinic_lead_gen"
    assert campaign["metadata"]["source_business_intent"]["industry"] == "dental"

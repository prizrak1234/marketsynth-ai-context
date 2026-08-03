"""Phase AI.214 — Campaign brief intake regression."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.helpers.business_operator_helpers import (
    analyze_operator,
    complete_and_confirm_brief,
    create_operator_campaign,
)
from tests.helpers.v2_specialist_execution_helpers import create_project


def test_vague_request_returns_missing_brief_questions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 vague brief")
    body = analyze_operator(client, auth_headers, project_id, "хочу клиентов")
    assert body["brief_completeness"]["passed"] is False
    assert body["brief_completeness"]["score"] < body["brief_completeness"]["threshold"]
    required_fields = {
        question["field"]
        for question in body["brief_completeness"]["missing_questions"]
        if question["required"]
    }
    assert "offer" in required_fields
    assert "target_audience" in required_fields


def test_dental_request_returns_partial_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 dental partial")
    body = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    assert body["confidence_gate_passed"] is True
    assert body["brief_draft"]["industry"] == "dental"
    assert body["brief_draft"]["goal"] == "lead_generation"
    assert body["brief_completeness"]["passed"] is False
    assert body["brief_draft"]["offer"] is None


def test_brief_answers_improve_completeness(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 brief answers")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    completed = client.post(
        f"/projects/{project_id}/business-operator/brief/complete",
        json={
            "intent": analyzed["intent"],
            "recommended_scenario": analyzed["recommended_scenario"],
            "brief": analyzed["brief_draft"],
            "answers": {
                "offer": "Dental implants and hygiene packages",
                "target_audience": "Adults 30-55 in the city",
            },
        },
        headers=auth_headers,
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["brief_completeness"]["passed"] is True
    assert body["brief_completeness"]["score"] >= body["brief_completeness"]["threshold"]
    assert body["brief_draft"]["offer"]
    assert body["brief_draft"]["target_audience"]


def test_cannot_create_campaign_without_confirmed_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 create blocked")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    from uuid import uuid4

    blocked = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"intent": analyzed["intent"], "brief_id": str(uuid4())},
        headers=auth_headers,
    )
    assert blocked.status_code == 409


def test_confirmed_brief_creates_campaign_with_provenance(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 create ok")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    brief_id = complete_and_confirm_brief(
        client,
        auth_headers,
        project_id,
        analyzed,
        extra_answers={
            "offer": "Dental implants and hygiene packages",
            "target_audience": "Adults 30-55 in the city",
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    campaign = created["campaign"]
    assert campaign["metadata"]["source_campaign_brief_id"] == brief_id
    assert campaign["metadata"]["source_business_intent"]["industry"] == "dental"


def test_plan_gets_safe_brief_context_from_wizard(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.214 plan context")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    brief_id = complete_and_confirm_brief(
        client,
        auth_headers,
        project_id,
        analyzed,
        extra_answers={
            "offer": "Dental implants and hygiene packages",
            "target_audience": "Adults 30-55 in the city",
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    campaign_id = created["campaign"]["id"]

    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    assert wizard.status_code == 201
    run_id = wizard.json()["id"]

    advanced = client.post(
        f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
        headers=auth_headers,
    )
    assert advanced.status_code == 200
    plan_id = advanced.json()["step_results"]["marketing_plan_id"]

    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    )
    assert plan.status_code == 200
    context = plan.json()["project_context"]
    assert context.get("campaign_brief_summary")
    assert context["campaign_brief_summary"]["brief_id"] == brief_id
    assert context["campaign_brief_summary"]["offer"]

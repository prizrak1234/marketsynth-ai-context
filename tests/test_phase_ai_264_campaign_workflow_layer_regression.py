"""Phase AI.264 — Campaign workflow layer regression."""

from __future__ import annotations

import pytest
from app.marketing.workflows.registry import WORKFLOW_STEP_ACTION_TYPES, list_workflow_templates
from app.schemas.contracts import CampaignActionType, CampaignWorkflowRunStatus
from fastapi.testclient import TestClient
from tests.helpers.business_operator_helpers import (
    analyze_operator,
    complete_and_confirm_brief,
    create_operator_campaign,
)
from tests.helpers.v2_specialist_execution_helpers import create_project


@pytest.fixture
def enable_marketing_skills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_SKILLS_ENABLED", "true")
    monkeypatch.setenv("MARKETING_DATA_TOOLS_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()


def _operator_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
    label: str,
    *,
    extra_answers: dict[str, str] | None = None,
) -> tuple[str, str]:
    project_id = create_project(client, auth_headers, label)
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
            "success_metric": "Qualified dental leads per month",
            **(extra_answers or {}),
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    return project_id, created["campaign"]["id"]


def test_registry_has_five_templates_with_mapped_actions() -> None:
    templates = list_workflow_templates()
    template_ids = {template.id for template in templates}
    assert template_ids == {
        "lead_gen_campaign",
        "content_machine",
        "offer_validation",
        "metrica_traffic_diagnostics",
        "visual_content_pack",
    }
    for template in templates:
        assert template.steps, f"{template.id} must define steps"
        for step in template.steps:
            assert step.recommended_action_type is not None, step.step_id
            assert step.recommended_action_type in WORKFLOW_STEP_ACTION_TYPES


def test_workflow_recommendations_are_read_only_in_control_center(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.264 read-only recs")

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200, center.text
    payload = center.json()
    suggestions = payload.get("workflow_suggestions") or []
    assert suggestions, "lead-gen campaign should receive workflow suggestions"
    assert payload.get("active_workflow") is None

    templates = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/workflows/templates",
        headers=auth_headers,
    )
    assert templates.status_code == 200
    assert len(templates.json()) == 5


def test_supervisor_gaps_can_trigger_workflow_recommendation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.264 supervisor workflow")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Campaign without confirmed brief",
            "goal": "Dental leads",
            "scenario_id": "dental_clinic_lead_gen",
            "metadata": {
                "source_business_intent": {
                    "goal": "lead_generation",
                    "industry": "dental",
                    "confidence": 0.7,
                    "recommended_scenario": "dental_clinic_lead_gen",
                },
            },
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert report.status_code == 200
    assert report.json()["findings"]

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    template_ids = {item["template_id"] for item in center.json().get("workflow_suggestions") or []}
    assert "offer_validation" in template_ids or "lead_gen_campaign" in template_ids


def test_create_workflow_run_has_no_skill_side_effects(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.264 create run")

    before = client.get(
        f"/projects/{project_id}/marketing-skills/runs?campaign_id={campaign_id}",
        headers=auth_headers,
    )
    assert before.status_code == 200
    before_count = len(before.json())

    created = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/workflows/lead_gen_campaign/create-run",
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["template_id"] == "lead_gen_campaign"
    assert body["status"] in {CampaignWorkflowRunStatus.DRAFT, CampaignWorkflowRunStatus.ACTIVE}
    assert body["current_step_index"] == 0
    assert body["step_results"] == {}

    after = client.get(
        f"/projects/{project_id}/marketing-skills/runs?campaign_id={campaign_id}",
        headers=auth_headers,
    )
    assert after.status_code == 200
    assert len(after.json()) == before_count

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    active = center.json().get("active_workflow")
    assert active is not None
    assert active["run"]["template_id"] == "lead_gen_campaign"
    assert active["steps"]
    assert active["progress_percent"] >= 0


def test_workflow_steps_recommend_existing_campaign_actions(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.264 step mapping")

    client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/workflows/content_machine/create-run",
        headers=auth_headers,
    )

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    active = center.json()["active_workflow"]
    action_types = {
        step["recommended_action_type"]
        for step in active["steps"]
        if step.get("recommended_action_type")
    }
    allowed = {action.value for action in CampaignActionType}
    assert action_types.issubset(allowed)
    assert CampaignActionType.CREATE_CONTENT_ASSET.value in action_types
    assert CampaignActionType.RUN_MEANING_UNPACKING.value in action_types


def test_create_run_rejects_unknown_template(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.264 unknown template")

    response = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/workflows/not_a_real_workflow/create-run",
        headers=auth_headers,
    )
    assert response.status_code == 409

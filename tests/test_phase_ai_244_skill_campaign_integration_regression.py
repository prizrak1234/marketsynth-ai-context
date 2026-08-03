"""Phase AI.244 — Skill-campaign integration regression."""

from __future__ import annotations

import pytest
from app.schemas.contracts import CampaignActionType
from fastapi.testclient import TestClient
from tests.helpers.business_operator_helpers import (
    analyze_operator,
    complete_and_confirm_brief,
    create_operator_campaign,
)
from tests.helpers.v2_specialist_execution_helpers import create_project
from tests.test_phase_ai_174_campaign_action_center_regression import execute_action


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
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    return project_id, created["campaign"]["id"]


def test_control_center_skill_suggestions_include_campaign_fields(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.244 suggestions")

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    suggestions = body.get("skill_suggestions") or []
    assert suggestions
    first = suggestions[0]
    assert first.get("reason")
    assert first.get("priority") >= 1
    assert first.get("expected_output")
    assert "segment_research" in {item["skill_type"] for item in suggestions}

    runs_before = client.get(
        f"/projects/{project_id}/marketing-skills/runs",
        headers=auth_headers,
    )
    assert runs_before.status_code == 200
    assert runs_before.json() == []


def test_skill_action_runs_exactly_one_skill(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.244 action run")

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    actions = center.json().get("available_actions") or []
    skill_actions = [
        action
        for action in actions
        if action["type"] == CampaignActionType.RUN_SEGMENT_RESEARCH.value and action["enabled"]
    ]
    assert skill_actions, actions

    result = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.RUN_SEGMENT_RESEARCH.value,
    )
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["action_type"] == CampaignActionType.RUN_SEGMENT_RESEARCH.value
    assert payload["created_resource_type"] == "marketing_skill_run"
    assert payload["created_resource_id"]

    listed = client.get(
        f"/projects/{project_id}/marketing-skills/runs",
        params={"campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    runs = listed.json()
    assert len(runs) == 1
    assert runs[0]["skill_type"] == "segment_research"
    assert runs[0]["status"] == "succeeded"
    assert runs[0]["used_tool_call_ids"] == []


def test_skill_output_merges_into_campaign_context_and_timeline(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.244 context")

    executed = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.RUN_SEGMENT_RESEARCH.value,
    )
    assert executed.status_code == 200

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    latest_runs = body.get("latest_skill_runs") or []
    assert len(latest_runs) == 1
    assert latest_runs[0]["output_payload"].get("provenance", {}).get("campaign_id") == campaign_id

    skill_context = body.get("skill_context") or {}
    assert skill_context.get("segment_summary")
    assert skill_context.get("source_run_ids", {}).get("segment_summary")

    timeline_types = {event["event_type"] for event in body.get("timeline") or []}
    assert "skill_run" in timeline_types

    run_id = latest_runs[0]["id"]
    fetched = client.get(
        f"/projects/{project_id}/marketing-skills/runs/{run_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["output_payload"]["provenance"]["skill_run_id"] == run_id


def test_wizard_plan_receives_safe_skill_summaries(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.244 plan context")

    executed = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.RUN_SEGMENT_RESEARCH.value,
    )
    assert executed.status_code == 200

    started = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
    )
    assert started.status_code == 200

    advanced = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.ADVANCE_WIZARD.value,
    )
    assert advanced.status_code == 200
    snapshot = advanced.json().get("control_center_snapshot") or {}
    plan_id = snapshot.get("resource_ids", {}).get("marketing_plan_id")
    assert plan_id

    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    )
    assert plan.status_code == 200
    summaries = plan.json()["project_context"].get("campaign_skill_summaries") or {}
    assert summaries.get("segment_summary")
    assert "rows" not in str(summaries)
    assert "wordstat_summary" not in str(summaries)


def test_skill_action_wordstat_does_not_call_tools_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.244 no tools")

    result = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.RUN_WORDSTAT_RESEARCH.value,
    )
    assert result.status_code == 200, result.text

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    run = (center.json().get("latest_skill_runs") or [])[0]
    assert run["skill_type"] == "wordstat_research"
    assert run["used_tool_call_ids"] == []

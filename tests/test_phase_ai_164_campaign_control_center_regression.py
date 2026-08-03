"""Phase AI.164 — Campaign control center regression."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.marketing.scenario_wizard_steps import SCENARIO_WIZARD_STEPS
from app.schemas.contracts import (
    CampaignHealthStatus,
    CampaignNextActionType,
    ScenarioWizardRunStatus,
)
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


def test_new_campaign_recommends_start_wizard(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 start wizard")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Control center new",
            "goal": "Test next action",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200, center.text
    body = center.json()
    assert body["health"]["status"] == CampaignHealthStatus.HEALTHY.value
    assert body["next_action"]["action_type"] == CampaignNextActionType.START_WIZARD.value
    assert body["timeline"] == []
    assert body["metrics"]["plans_total"] == 0


def test_campaign_without_scenario_is_blocked(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 blocked")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={"name": "No scenario", "goal": "Blocked path"},
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body["health"]["status"] == CampaignHealthStatus.BLOCKED.value
    assert body["next_action"]["action_type"] == CampaignNextActionType.ATTACH_SCENARIO.value
    assert body["health"]["blocking_reason"]


def test_running_wizard_recommends_advance_wizard(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 advance wizard")
    campaign = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Wizard running",
            "goal": "Advance recommendation",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = campaign.json()["id"]
    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    assert wizard.status_code == 201

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body["next_action"]["action_type"] == CampaignNextActionType.ADVANCE_WIZARD.value
    assert body["health"]["status"] == CampaignHealthStatus.WAITING_FOR_USER.value
    assert body["timeline"]
    assert body["resource_ids"]["wizard_run_id"]


def test_after_create_plan_step_recommends_approve_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 approve plan")
    campaign = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Draft plan",
            "goal": "Plan approval",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = campaign.json()["id"]
    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    run_id = wizard.json()["id"]
    advanced = client.post(
        f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
        headers=auth_headers,
    )
    assert advanced.status_code == 200

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body["next_action"]["action_type"] == CampaignNextActionType.ADVANCE_WIZARD.value
    assert body["metrics"]["plans_total"] >= 1
    assert body["resource_ids"]["marketing_plan_id"]


def test_completed_wizard_campaign_control_center(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 completed")
    campaign = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Full pipeline",
            "goal": "Completed state",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = campaign.json()["id"]
    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    run_id = wizard.json()["id"]
    run_body = wizard.json()
    for _ in range(len(SCENARIO_WIZARD_STEPS)):
        if run_body["status"] in {
            ScenarioWizardRunStatus.SUCCEEDED.value,
            ScenarioWizardRunStatus.FAILED.value,
        }:
            break
        advanced = client.post(
            f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
            headers=auth_headers,
        )
        assert advanced.status_code == 200, advanced.text
        run_body = advanced.json()

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body["health"]["status"] == CampaignHealthStatus.COMPLETED.value
    assert body["next_action"]["action_type"] == CampaignNextActionType.SCHEDULE_OR_DRY_RUN.value
    assert body["health"]["progress_percent"] == 100
    assert body["metrics"]["jobs_total"] >= 1
    assert len(body["timeline"]) >= len(SCENARIO_WIZARD_STEPS)


def test_list_control_view_filters_by_health(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 list filter")
    client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Healthy one",
            "goal": "Filter test",
            "scenario_id": "dental_clinic_lead_gen",
        },
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/business-campaigns",
        json={"name": "Blocked one", "goal": "No scenario"},
        headers=auth_headers,
    )

    healthy = client.get(
        f"/projects/{project_id}/business-campaigns",
        params={"view": "control", "health": "healthy"},
        headers=auth_headers,
    )
    assert healthy.status_code == 200
    assert all(row["health"]["status"] == "healthy" for row in healthy.json())

    blocked = client.get(
        f"/projects/{project_id}/business-campaigns/search",
        params={"view": "control", "health": "blocked"},
        headers=auth_headers,
    )
    assert blocked.status_code == 200
    assert all(row["health"]["status"] == "blocked" for row in blocked.json())


def test_control_center_has_safe_warnings_and_no_auto_recovery(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 warnings")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={"name": "Warnings", "goal": "Check hints"},
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    body = center.json()
    assert body["recovery_hint"] is None
    assert any("scenario" in warning.lower() for warning in body["safe_warnings"])


@pytest.mark.asyncio
async def test_next_action_types_are_recommendations_only(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.164 read only")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Read only",
            "goal": "No side effects",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    before_plans = client.get(
        f"/projects/{project_id}/marketing-plans",
        headers=auth_headers,
    ).json()

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    assert center.json()["next_action"]["action_type"] == CampaignNextActionType.START_WIZARD.value

    after_plans = client.get(
        f"/projects/{project_id}/marketing-plans",
        headers=auth_headers,
    ).json()
    assert len(after_plans) == len(before_plans)

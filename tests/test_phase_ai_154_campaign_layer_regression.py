"""Phase AI.154 — Business campaign layer regression."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.marketing.scenario_wizard_steps import SCENARIO_WIZARD_STEPS
from app.schemas.contracts import CampaignStatus, ScenarioWizardRunStatus
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


def conflict_message(response) -> str:
    body = response.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def test_create_business_campaign(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = create_project(client, auth_headers, "AI.154 campaign create")
    response = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Dental launch",
            "goal": "Generate leads for new clinic",
            "scenario_id": "dental_clinic_lead_gen",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Dental launch"
    assert body["scenario_id"] == "dental_clinic_lead_gen"
    assert body["status"] == CampaignStatus.DRAFT.value


def test_attach_scenario_via_patch(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = create_project(client, auth_headers, "AI.154 scenario attach")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={"name": "SaaS push", "goal": "Acquire trial users"},
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    assert created.json()["scenario_id"] is None

    patched = client.patch(
        f"/projects/{project_id}/business-campaigns/{campaign_id}",
        json={"scenario_id": "telegram_bot_saas_launch"},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["scenario_id"] == "telegram_bot_saas_launch"


def test_campaign_wizard_flow_tags_provenance_and_metrics(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.154 campaign wizard")
    campaign = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Wizard campaign",
            "goal": "Full pipeline from campaign container",
            "scenario_id": "local_service_promo",
            "status": "active",
        },
        headers=auth_headers,
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]

    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    assert wizard.status_code == 201, wizard.text
    run_id = wizard.json()["id"]
    assert wizard.json()["source_campaign_id"] == campaign_id

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

    assert run_body["status"] == ScenarioWizardRunStatus.SUCCEEDED.value
    plan_id = run_body["step_results"]["marketing_plan_id"]
    job_id = run_body["step_results"]["publication_package_job_id"]

    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    )
    assert plan.status_code == 200
    assert plan.json()["project_context"]["source_campaign_id"] == campaign_id

    provenance = client.get(
        f"/projects/{project_id}/provenance/content-production/{job_id}",
        headers=auth_headers,
    )
    assert provenance.status_code == 200
    assert provenance.json()["source_campaign_id"] == campaign_id

    metrics = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/metrics",
        headers=auth_headers,
    )
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["plans_total"] >= 1
    assert body["assets_total"] >= 1
    assert body["packages_total"] >= 1
    assert body["jobs_total"] >= 1
    assert body["wizard_runs_total"] >= 1

    dashboard = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/dashboard",
        headers=auth_headers,
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["campaign"]["id"] == campaign_id
    assert dashboard.json()["metrics"]["plans_total"] >= 1


def test_campaign_search_by_name_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.154 campaign search")
    client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Unique Alpha Campaign",
            "goal": "Search target",
            "scenario_id": "expert_blogger_content_machine",
            "status": "paused",
        },
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/business-campaigns",
        json={"name": "Other", "goal": "Ignore me", "status": "draft"},
        headers=auth_headers,
    )

    by_name = client.get(
        f"/projects/{project_id}/business-campaigns/search",
        params={"q": "Alpha"},
        headers=auth_headers,
    )
    assert by_name.status_code == 200
    assert len(by_name.json()) == 1
    assert by_name.json()[0]["name"] == "Unique Alpha Campaign"

    by_status = client.get(
        f"/projects/{project_id}/business-campaigns/search",
        params={"status": "paused"},
        headers=auth_headers,
    )
    assert by_status.status_code == 200
    assert all(row["status"] == "paused" for row in by_status.json())

    by_scenario = client.get(
        f"/projects/{project_id}/business-campaigns/search",
        params={"scenario_id": "expert_blogger_content_machine"},
        headers=auth_headers,
    )
    assert by_scenario.status_code == 200
    assert len(by_scenario.json()) >= 1


def test_legacy_scenario_wizard_flow_still_works(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.154 legacy wizard")
    created = client.post(
        f"/projects/{project_id}/scenario-wizard-runs",
        json={"scenario_id": "local_service_promo"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["source_campaign_id"] is None


@pytest.mark.asyncio
async def test_campaign_provenance_helper(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    from app.demo.provenance_helpers import build_content_production_provenance

    project_id = create_project(client, auth_headers, "AI.154 provenance helper")
    campaign = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Prov campaign",
            "goal": "Provenance check",
            "scenario_id": "dental_clinic_lead_gen",
        },
        headers=auth_headers,
    )
    campaign_id = campaign.json()["id"]
    owner_id = UUID(campaign.json()["owner_id"])

    wizard = client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/scenario-wizard-runs",
        headers=auth_headers,
    )
    run_id = wizard.json()["id"]
    run_body = wizard.json()
    while run_body["status"] not in {
        ScenarioWizardRunStatus.SUCCEEDED.value,
        ScenarioWizardRunStatus.FAILED.value,
    }:
        advanced = client.post(
            f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
            headers=auth_headers,
        )
        assert advanced.status_code == 200
        run_body = advanced.json()

    job_id = run_body["step_results"]["publication_package_job_id"]
    provenance = await build_content_production_provenance(
        db_session,
        owner_id,
        UUID(project_id),
        UUID(job_id),
    )
    assert provenance is not None
    assert provenance.source_campaign_id == campaign_id

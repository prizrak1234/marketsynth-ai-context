"""Phase AI.144 — Scenario wizard regression."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.marketing.scenario_wizard_steps import SCENARIO_WIZARD_STEPS
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.schemas.contracts import ScenarioWizardRunStatus
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


def conflict_message(response) -> str:
    body = response.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def test_wizard_has_fifteen_manual_steps() -> None:
    assert len(SCENARIO_WIZARD_STEPS) == 15
    assert SCENARIO_WIZARD_STEPS[-1] == "create_dry_run_job"


def test_create_wizard_run_for_dental_scenario(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.144 wizard create")
    response = client.post(
        f"/projects/{project_id}/scenario-wizard-runs",
        json={"scenario_id": "dental_clinic_lead_gen"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scenario_id"] == "dental_clinic_lead_gen"
    assert body["status"] == ScenarioWizardRunStatus.DRAFT.value
    assert body["current_step"] == "create_plan"
    assert body["step_results"] == {}


def test_dental_wizard_advances_step_by_step_to_queued_dry_run_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.144 wizard advance")
    created = client.post(
        f"/projects/{project_id}/scenario-wizard-runs",
        json={"scenario_id": "dental_clinic_lead_gen"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    run_body = created.json()
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
    assert run_body["current_step"] == "create_dry_run_job"
    results = run_body["step_results"]
    assert results.get("marketing_plan_id")
    assert results.get("execution_run_id")
    assert results.get("content_asset_id")
    assert results.get("publication_package_job_id")
    assert len(results.get("steps_completed") or []) == len(SCENARIO_WIZARD_STEPS)

    job = client.get(
        f"/projects/{project_id}/publication-package-jobs/{results['publication_package_job_id']}",
        headers=auth_headers,
    )
    assert job.status_code == 200
    assert job.json()["status"] == PublicationPackageJobStatus.QUEUED.value


def test_advance_on_succeeded_wizard_returns_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.144 wizard terminal")
    created = client.post(
        f"/projects/{project_id}/scenario-wizard-runs",
        json={"scenario_id": "local_service_promo"},
        headers=auth_headers,
    )
    run_id = created.json()["id"]
    run_body = created.json()
    while run_body["status"] not in {
        ScenarioWizardRunStatus.SUCCEEDED.value,
        ScenarioWizardRunStatus.FAILED.value,
    }:
        advanced = client.post(
            f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
            headers=auth_headers,
        )
        assert advanced.status_code == 200, advanced.text
        run_body = advanced.json()

    assert run_body["status"] == ScenarioWizardRunStatus.SUCCEEDED.value
    again = client.post(
        f"/projects/{project_id}/scenario-wizard-runs/{run_id}/advance",
        headers=auth_headers,
    )
    assert again.status_code == 409
    assert "already" in conflict_message(again).lower()


@pytest.mark.asyncio
async def test_wizard_provenance_includes_wizard_run_id(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    from app.demo.provenance_helpers import build_content_production_provenance
    from app.services.e2e_demo_seed_service import E2eDemoSeedService

    bootstrap = client.post(
        "/projects",
        json={"name": "AI.144 wizard provenance"},
        headers=auth_headers,
    )
    owner_id = UUID(bootstrap.json()["owner_id"])

    seed = await E2eDemoSeedService(db_session).seed(
        owner_id=owner_id,
        wizard=True,
        scenario="dental_clinic_lead_gen",
    )
    await db_session.commit()

    assert seed.wizard_run_id is not None
    project_id = seed.project_id

    wizard_run = client.get(
        f"/projects/{project_id}/scenario-wizard-runs/{seed.wizard_run_id}",
        headers=auth_headers,
    )
    assert wizard_run.status_code == 200
    job_id = wizard_run.json()["step_results"]["publication_package_job_id"]

    provenance = await build_content_production_provenance(
        db_session,
        owner_id,
        project_id,
        UUID(job_id),
    )
    assert provenance is not None
    assert provenance.source_wizard_run_id == str(seed.wizard_run_id)

    http = client.get(
        f"/projects/{project_id}/provenance/content-production/{job_id}",
        headers=auth_headers,
    )
    assert http.status_code == 200
    assert http.json()["source_wizard_run_id"] == str(seed.wizard_run_id)

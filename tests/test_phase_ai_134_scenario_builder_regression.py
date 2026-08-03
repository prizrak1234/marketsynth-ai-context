"""Phase AI.134 — Product Scenario Builder regression."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.agents.marketer.marketing_specialist_registry import (
    FROZEN_PIPELINE_ORDER,
    list_marketing_specialists,
)
from app.demo.provenance_helpers import build_content_production_provenance
from app.marketing.scenarios import SCENARIO_IDS, get_scenario, list_scenarios
from app.schemas.contracts import MarketingPlanStatus, MarketingSpecialistType
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from app.services.marketing_pipeline_execution_service import (
    V2_SPECIALIST_DEPENDENCIES,
    MarketingPipelineExecutionService,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.v2_specialist_execution_helpers import create_project


def test_scenario_registry_has_five_valid_templates() -> None:
    scenarios = list_scenarios()
    assert len(scenarios) == 5
    assert set(SCENARIO_IDS) == {scenario.id for scenario in scenarios}
    registered = {profile.specialist_type for profile in list_marketing_specialists()}
    for scenario in scenarios:
        assert scenario.required_specialists
        assert len(scenario.default_plan_tasks) == len(scenario.required_specialists)
        task_specialists = [task.specialist for task in scenario.default_plan_tasks]
        assert task_specialists == list(scenario.required_specialists)
        assert set(scenario.required_specialists).issubset(registered)


def test_list_marketing_scenarios_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.134 scenarios list")
    response = client.get(
        f"/projects/{project_id}/marketing-scenarios",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    ids = {item["id"] for item in body}
    assert "dental_clinic_lead_gen" in ids


def test_create_plan_from_scenario_matches_template(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.134 create plan")
    scenario_id = "dental_clinic_lead_gen"
    template = get_scenario(scenario_id)
    assert template is not None

    response = client.post(
        f"/projects/{project_id}/marketing-scenarios/{scenario_id}/create-plan",
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["status"] == MarketingPlanStatus.DRAFT.value
    assert plan["source_scenario_id"] == scenario_id
    assert plan["source_scenario_name"] == template.name
    assert plan["goal"] == template.goal
    assert [task["specialist"] for task in plan["specialist_tasks"]] == [
        specialist.value for specialist in template.required_specialists
    ]


def test_create_plan_from_unknown_scenario_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.134 unknown scenario")
    response = client.post(
        f"/projects/{project_id}/marketing-scenarios/not_a_scenario/create-plan",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_scenario_plan_uses_existing_execution_pipeline(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.134 execution guard")
    created = client.post(
        f"/projects/{project_id}/marketing-scenarios/local_service_promo/create-plan",
        headers=auth_headers,
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    approved = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200

    run_created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    )
    assert run_created.status_code == 201
    run = run_created.json()
    assert len(run["task_snapshots"]) == len(created.json()["specialist_tasks"])
    assert [snap["specialist"] for snap in run["task_snapshots"]] == [
        task["specialist"] for task in created.json()["specialist_tasks"]
    ]


def test_frozen_layers_unchanged_by_scenario_builder() -> None:
    assert list(FROZEN_PIPELINE_ORDER) == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
    ]
    assert MarketingPipelineExecutionService.pipeline_order() == list(FROZEN_PIPELINE_ORDER)
    assert len(V2_SPECIALIST_DEPENDENCIES) == 8
    assert MarketingSpecialistType.CRO_SPECIALIST in V2_SPECIALIST_DEPENDENCIES


@pytest.mark.asyncio
async def test_provenance_includes_scenario_when_plan_has_source(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.134 provenance"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    from app.db.repositories.marketing_plans import MarketingPlanRepository

    plan = await MarketingPlanRepository(db_session).get_by_id_for_owner(
        seed.marketing_plan_id,
        owner_id,
        seed.project_id,
    )
    assert plan is not None
    plan.source_scenario_id = "dental_clinic_lead_gen"
    plan.source_scenario_name = "Dental Clinic Lead Gen"
    await MarketingPlanRepository(db_session).update(plan)
    await db_session.commit()

    provenance = await build_content_production_provenance(
        db_session,
        owner_id,
        seed.project_id,
        seed.publication_package_job_id,
    )
    assert provenance is not None
    assert provenance.source_scenario_id == "dental_clinic_lead_gen"
    assert provenance.source_scenario_name == "Dental Clinic Lead Gen"

    http = client.get(
        f"/projects/{seed.project_id}/provenance/content-production/"
        f"{seed.publication_package_job_id}",
        headers=auth_headers,
    )
    assert http.status_code == 200
    body = http.json()
    assert body["source_scenario_id"] == "dental_clinic_lead_gen"
    assert body["source_scenario_name"] == "Dental Clinic Lead Gen"

"""Phase AI.116 — CRO Specialist execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.schemas.contracts import MarketingPlanExecutionTaskStatus, MarketingSpecialistType
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.v2_specialist_execution_helpers import (
    conflict_message,
    create_approved_plan_with_specialists,
    create_project,
    execute_specialist,
    execute_through,
    owner_id_for_project,
    start_run,
    task_index_for,
)

_PLAN = [
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.FUNNEL_ARCHITECT,
    MarketingSpecialistType.SALES_COPYWRITER,
    MarketingSpecialistType.CRO_SPECIALIST,
]
_KEYS = (
    "conversion_bottlenecks",
    "landing_page_recommendations",
    "cta_improvements",
    "trust_elements",
    "form_optimization",
    "test_hypotheses",
    "priority_actions",
)


@pytest.mark.asyncio
async def test_cannot_execute_cro_before_sales_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.116 CRO guard")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN[:-2])
    response = execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        task_index_for(run, MarketingSpecialistType.CRO_SPECIALIST),
    )
    assert response.status_code == 409
    assert "Sales Copywriter" in conflict_message(response)


@pytest.mark.asyncio
async def test_cro_executes_with_cro_recommendations_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.116 CRO happy")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN[:-1])
    cro_index = task_index_for(run, MarketingSpecialistType.CRO_SPECIALIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], cro_index)
    assert response.status_code == 201, response.text
    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "cro_recommendations"
    for key in _KEYS:
        assert output["structured_data"][key]
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert (
        run_after["task_snapshots"][cro_index]["status"]
        == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    )


@pytest.mark.asyncio
async def test_duplicate_cro_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.116 CRO duplicate")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN)
    cro_index = task_index_for(run, MarketingSpecialistType.CRO_SPECIALIST)
    assert execute_specialist(client, auth_headers, project_id, run["id"], cro_index).status_code == 409

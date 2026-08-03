"""Shared helpers for v2 marketing specialist execution tests (AI.111–AI.115)."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.marketing_specialist_registry import (
    V2_DEMO_EXECUTION_ORDER,
    get_marketing_specialist,
)
from app.schemas.contracts import (
    MarketingExecutionPlan,
    MarketingSpecialistTask,
    MarketingSpecialistType,
)
from app.services.marketing_plan_service import MarketingPlanService
from app.services.projects_service import ProjectService


def conflict_message(response) -> str:
    body = response.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def create_project(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def create_approved_plan_with_specialists(
    db_session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    specialists: list[MarketingSpecialistType],
) -> UUID:
    tasks = [
        MarketingSpecialistTask(
            specialist=specialist,
            objective=get_marketing_specialist(specialist).default_objective,
            expected_output=get_marketing_specialist(specialist).default_expected_output,
        )
        for specialist in specialists
    ]
    plan = MarketingExecutionPlan(
        goal="V2 marketing specialist execution test plan",
        specialist_tasks=tasks,
    )
    service = MarketingPlanService(db_session)
    row = await service.create_from_execution_plan(owner_id, project_id, plan)
    assert row is not None
    approved = await service.approve(owner_id, project_id, row.id)
    assert approved is not None
    await db_session.commit()
    return row.id


async def owner_id_for_project(db_session: AsyncSession, project_id: str) -> UUID:
    project = await ProjectService(db_session).get_by_id(UUID(project_id))
    assert project is not None
    return project.owner_id


def start_run(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: UUID | str,
) -> dict:
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    started = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}/start",
        headers=headers,
    )
    assert started.status_code == 200, started.text
    return client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}",
        headers=headers,
    ).json()


def task_index_for(run: dict, specialist: MarketingSpecialistType) -> int:
    return next(
        index
        for index, task in enumerate(run["task_snapshots"])
        if task["specialist"] == specialist.value
    )


def execute_specialist(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    run_id: str,
    task_index: int,
):
    return client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/tasks/{task_index}/execute-specialist",
        headers=headers,
    )


def execute_through(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    run: dict,
    specialists: list[MarketingSpecialistType],
) -> dict:
    current = run
    for specialist in specialists:
        index = task_index_for(current, specialist)
        response = execute_specialist(client, headers, project_id, current["id"], index)
        assert response.status_code == 201, response.text
        current = client.get(
            f"/projects/{project_id}/marketing-plan-execution-runs/{current['id']}",
            headers=headers,
        ).json()
    return current


V2_REGRESSION_SPECIALISTS: list[MarketingSpecialistType] = list(V2_DEMO_EXECUTION_ORDER)

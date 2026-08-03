"""Phase AI.38 — Marketing plan execution run auto-completion."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"

_MVP_SPECIALISTS = tuple(MarketingSpecialistType)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.38 Completion"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": agent_type},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _approved_plan_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    orchestrator_id = _create_agent(client, headers, project_id, agent_type="orchestrator")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": STRATEGY_MESSAGE, "agent_id": orchestrator_id},
        headers=headers,
    ).json()
    saved = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=headers,
    ).json()
    plan_id = saved["created_resource_id"]
    approved = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    return plan_id


def _start_run(client: TestClient, headers: dict[str, str], project_id: str, plan_id: str) -> dict:
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}/start",
        headers=headers,
    )
    return client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}",
        headers=headers,
    ).json()


def _task_index_for(run: dict, specialist: MarketingSpecialistType) -> int:
    return next(
        index
        for index, task in enumerate(run["task_snapshots"])
        if task["specialist"] == specialist.value
    )


def _execute_specialist(
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


def test_run_stays_running_until_all_tasks_completed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        strategist_index,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["execution_run_status"] == MarketingPlanExecutionStatus.RUNNING.value
    assert body["run_completed"] is False
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert run_after["status"] == MarketingPlanExecutionStatus.RUNNING.value


@pytest.mark.asyncio
async def test_run_succeeds_after_final_analyst_execution(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)

    last_response = None
    for specialist in _MVP_SPECIALISTS:
        try:
            index = _task_index_for(run, specialist)
        except StopIteration:
            continue
        last_response = _execute_specialist(
            client,
            auth_headers,
            project_id,
            run["id"],
            index,
        )
        assert last_response.status_code == 201, last_response.text
        if specialist != MarketingSpecialistType.ANALYST:
            run = client.get(
                f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
                headers=auth_headers,
            ).json()
            assert run["status"] == MarketingPlanExecutionStatus.RUNNING.value

    assert last_response is not None
    final_body = last_response.json()
    assert final_body["execution_run_status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    assert final_body["run_completed"] is True

    run_final = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert run_final["status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    summary = run_final["result_summary"]
    assert summary["mode"] == "specialist_pipeline"
    assert summary["task_count"] == len(run_final["task_snapshots"])
    completed = summary["completed_specialists"]
    for specialist in _MVP_SPECIALISTS:
        if any(t["specialist"] == specialist.value for t in run_final["task_snapshots"]):
            assert specialist.value in completed
    output_map = summary["output_ids_by_specialist"]
    assert len(output_map) >= 1
    for task in run_final["task_snapshots"]:
        if task["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value:
            assert task["specialist"] in output_map


@pytest.mark.asyncio
async def test_complete_if_all_tasks_completed_no_op_for_non_running(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    project_uuid = UUID(project_id)
    service = MarketingPlanExecutionService(db_session)

    queued = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    owner_id = UUID(queued["owner_id"])
    queued_row, queued_completed = await service.complete_if_all_tasks_completed(
        owner_id,
        project_uuid,
        UUID(queued["id"]),
    )
    assert queued_completed is False
    assert queued_row is not None
    assert queued_row.status == MarketingPlanExecutionStatus.QUEUED

    running = _start_run(client, auth_headers, project_id, plan_id)
    cancelled = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{running['id']}/cancel",
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    cancelled_row, cancelled_completed = await service.complete_if_all_tasks_completed(
        owner_id,
        project_uuid,
        UUID(running["id"]),
    )
    assert cancelled_completed is False
    assert cancelled_row is not None
    assert cancelled_row.status == MarketingPlanExecutionStatus.CANCELLED

    succeeded_run = _start_run(client, auth_headers, project_id, plan_id)
    for specialist in _MVP_SPECIALISTS:
        try:
            index = _task_index_for(succeeded_run, specialist)
        except StopIteration:
            continue
        _execute_specialist(client, auth_headers, project_id, succeeded_run["id"], index)
    succeeded_row, succeeded_completed = await service.complete_if_all_tasks_completed(
        owner_id,
        project_uuid,
        UUID(succeeded_run["id"]),
    )
    assert succeeded_completed is False
    assert succeeded_row is not None
    assert succeeded_row.status == MarketingPlanExecutionStatus.SUCCEEDED


def test_placeholder_completed_does_not_auto_complete_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{created['id']}/start",
        headers=auth_headers,
    )
    completed = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{created['id']}/complete-placeholder",
        headers=auth_headers,
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    assert body["result_summary"]["mode"] == "placeholder"
    assert all(
        t["status"] == MarketingPlanExecutionTaskStatus.PLACEHOLDER_COMPLETED.value
        for t in body["task_snapshots"]
    )


@pytest.mark.asyncio
async def test_no_child_runs_tools_or_assets_on_completion(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": STRATEGY_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(chat["session"]["owner_id"])
    parent_id = UUID(chat["agent_run_id"])
    before_children = await AgentRunService(db_session).count_children(parent_id, owner_id)

    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    for specialist in _MVP_SPECIALISTS:
        try:
            index = _task_index_for(run, specialist)
        except StopIteration:
            continue
        assert (
            _execute_specialist(client, auth_headers, project_id, run["id"], index).status_code
            == 201
        )

    after_children = await AgentRunService(db_session).count_children(parent_id, owner_id)
    assert after_children == before_children == 0

    project_uuid = UUID(project_id)
    tool_count = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolExecutionLogTable)
            .where(ToolExecutionLogTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0

    assets = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    assert assets == []

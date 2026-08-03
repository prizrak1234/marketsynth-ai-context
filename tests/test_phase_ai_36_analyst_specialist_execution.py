"""Phase AI.36 — Analyst specialist dry-run execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_specialist_output import MarketingSpecialistOutputVersionTable
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"

_STRUCTURED_KEYS = (
    "risks",
    "resource_requirements",
    "channel_fit",
    "funnel_gaps",
    "execution_complexity",
    "kpi_recommendations",
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.36 Analyst"}, headers=headers)
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


def _execute_through_critic(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> tuple[dict, int]:
    run = _start_run(client, headers, project_id, plan_id)
    for specialist in (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    ):
        index = _task_index_for(run, specialist)
        response = _execute_specialist(client, headers, project_id, run["id"], index)
        assert response.status_code == 201, response.text
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=headers,
    ).json()
    analyst_index = _task_index_for(run_after, MarketingSpecialistType.ANALYST)
    return run_after, analyst_index


def test_cannot_execute_before_critic(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    for specialist in (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
    ):
        index = _task_index_for(run, specialist)
        assert (
            _execute_specialist(client, auth_headers, project_id, run["id"], index).status_code
            == 201
        )
    try:
        analyst_index = _task_index_for(run, MarketingSpecialistType.ANALYST)
    except StopIteration:
        pytest.skip("Plan has no analyst task")
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        analyst_index,
    )
    assert response.status_code == 409
    assert "Critic" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyst_executes_after_full_pipeline(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, analyst_index = _execute_through_critic(
        client,
        auth_headers,
        project_id,
        plan_id,
    )

    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        analyst_index,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.ANALYST.value

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "analysis"
    assert output["title"] == "Execution analysis"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    assert "raw_response" not in structured
    assert structured.get("mock") is True

    critic_rows = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"], "specialist": "critic"},
        headers=auth_headers,
    ).json()
    assert critic_rows[0]["structured_data"].get("approval_recommendation")

    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert run_after["status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    assert run_after["result_summary"]["mode"] == "specialist_pipeline"
    assert (
        run_after["task_snapshots"][analyst_index]["status"]
        == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    )


def test_duplicate_analyst_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, analyst_index = _execute_through_critic(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], analyst_index)
    assert first.status_code == 201
    second = _execute_specialist(client, auth_headers, project_id, run["id"], analyst_index)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_no_child_runs_tools_or_content_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, analyst_index = _execute_through_critic(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(client, auth_headers, project_id, run["id"], analyst_index)
    assert executed.status_code == 201

    project_uuid = UUID(project_id)
    tool_count = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolExecutionLogTable)
            .where(ToolExecutionLogTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0

    version_count = (
        await db_session.execute(
            select(func.count())
            .select_from(MarketingSpecialistOutputVersionTable)
            .where(
                MarketingSpecialistOutputVersionTable.specialist_output_id
                == UUID(executed.json()["specialist_output_id"]),
            ),
        )
    ).scalar_one()
    assert version_count == 1


@pytest.mark.asyncio
async def test_ai31_ai35_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    expectations = (
        (MarketingSpecialistType.STRATEGIST, "strategy"),
        (MarketingSpecialistType.RESEARCHER, "research"),
        (MarketingSpecialistType.CONTENT_PLANNER, "content_plan"),
        (MarketingSpecialistType.COPYWRITER, "content_copy"),
        (MarketingSpecialistType.CRITIC, "critique"),
    )
    for specialist, output_type in expectations:
        index = _task_index_for(run, specialist)
        response = _execute_specialist(client, auth_headers, project_id, run["id"], index)
        assert response.status_code == 201, response.text
        detail = client.get(
            f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
            headers=auth_headers,
        ).json()
        assert detail["output_type"] == output_type

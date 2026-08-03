"""Phase AI.33 — Content Planner specialist dry-run execution."""

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
    "content_pillars",
    "funnel_stages",
    "post_ideas",
    "publishing_sequence",
    "channel_recommendations",
    "dependencies_for_copywriter",
    "risks",
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.33 Planner"}, headers=headers)
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


def _execute_strategist_and_researcher(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> tuple[dict, int]:
    run = _start_run(client, headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    assert (
        _execute_specialist(client, headers, project_id, run["id"], strategist_index).status_code
        == 201
    )
    researcher_index = _task_index_for(run, MarketingSpecialistType.RESEARCHER)
    assert (
        _execute_specialist(client, headers, project_id, run["id"], researcher_index).status_code
        == 201
    )
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=headers,
    ).json()
    planner_index = _task_index_for(run_after, MarketingSpecialistType.CONTENT_PLANNER)
    return run_after, planner_index


# --- Gates ---


def test_cannot_execute_content_planner_if_run_not_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    planner_index = _task_index_for(run, MarketingSpecialistType.CONTENT_PLANNER)
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        planner_index,
    )
    assert response.status_code == 409


def test_cannot_execute_before_strategist(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    planner_index = _task_index_for(run, MarketingSpecialistType.CONTENT_PLANNER)
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        planner_index,
    )
    assert response.status_code == 409
    assert "Strategist" in response.json()["detail"]


def test_cannot_execute_before_researcher(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    strategist_run = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        strategist_index,
    )
    assert strategist_run.status_code == 201
    planner_index = _task_index_for(run, MarketingSpecialistType.CONTENT_PLANNER)
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        planner_index,
    )
    assert response.status_code == 409
    assert "Researcher" in response.json()["detail"]


# --- Happy path ---


@pytest.mark.asyncio
async def test_content_planner_executes_after_strategist_and_researcher(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, planner_index = _execute_strategist_and_researcher(
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
        planner_index,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.CONTENT_PLANNER.value

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "content_plan"
    assert output["title"] == "Content plan"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    assert "raw_response" not in structured
    assert structured.get("mock") is True
    deps = structured["dependencies_for_copywriter"]
    assert any("copywriter" in str(item).lower() for item in deps)

    strategist_outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"], "specialist": "strategist"},
        headers=auth_headers,
    ).json()
    researcher_outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"], "specialist": "researcher"},
        headers=auth_headers,
    ).json()
    assert strategist_outputs
    assert researcher_outputs
    assert strategist_outputs[0]["structured_data"].get("positioning")
    assert researcher_outputs[0]["structured_data"].get("audience_segments")

    version_count = (
        await db_session.execute(
            select(func.count())
            .select_from(MarketingSpecialistOutputVersionTable)
            .where(
                MarketingSpecialistOutputVersionTable.specialist_output_id
                == UUID(body["specialist_output_id"]),
            ),
        )
    ).scalar_one()
    assert version_count == 1

    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert run_after["status"] == MarketingPlanExecutionStatus.RUNNING.value
    task_after = run_after["task_snapshots"][planner_index]
    assert task_after["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value


def test_duplicate_content_planner_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, planner_index = _execute_strategist_and_researcher(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], planner_index)
    assert first.status_code == 201
    second = _execute_specialist(client, auth_headers, project_id, run["id"], planner_index)
    assert second.status_code == 409


# --- Safety ---


@pytest.mark.asyncio
async def test_no_child_runs_tools_or_content_assets(
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
    run, planner_index = _execute_strategist_and_researcher(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(client, auth_headers, project_id, run["id"], planner_index)
    assert executed.status_code == 201

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

    llm_rows = (
        await db_session.execute(
            select(LLMRequestTable).where(LLMRequestTable.project_id == project_uuid),
        )
    ).scalars().all()
    for row in llm_rows:
        meta = row.request_metadata or {}
        tools_meta = meta.get("tools_metadata") or {}
        available = tools_meta.get("available_tool_names")
        assert available is None or available == []

    assets_before = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
    )
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{executed.json()['specialist_output_id']}/approve",
        headers=auth_headers,
    )
    assets_after = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
    )
    assert len(assets_after) == len(assets_before)


@pytest.mark.asyncio
async def test_ai31_ai32_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    strategist_run = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        strategist_index,
    )
    assert strategist_run.status_code == 201
    researcher_index = _task_index_for(run, MarketingSpecialistType.RESEARCHER)
    researcher = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        researcher_index,
    )
    assert researcher.status_code == 201
    researcher_output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{researcher.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert researcher_output["output_type"] == "research"

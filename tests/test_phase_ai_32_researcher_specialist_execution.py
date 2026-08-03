"""Phase AI.32 — Researcher specialist desk-research execution."""

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


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.32 Researcher"}, headers=headers)
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


def _execute_strategist_first(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> tuple[dict, int, int]:
    run = _start_run(client, headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    response = _execute_specialist(client, headers, project_id, run["id"], strategist_index)
    assert response.status_code == 201, response.text
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=headers,
    ).json()
    researcher_index = _task_index_for(run_after, MarketingSpecialistType.RESEARCHER)
    return run_after, strategist_index, researcher_index


# --- Gates ---


def test_cannot_execute_researcher_if_run_not_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    researcher_index = _task_index_for(run, MarketingSpecialistType.RESEARCHER)
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        researcher_index,
    )
    assert response.status_code == 409


def test_cannot_execute_researcher_before_strategist(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    researcher_index = _task_index_for(run, MarketingSpecialistType.RESEARCHER)

    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        researcher_index,
    )
    assert response.status_code == 409
    assert "Strategist" in response.json()["detail"]


def test_non_enabled_roles_still_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    pytest.skip("All MVP marketing specialists are enabled after AI.36")
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, _, researcher_index = _execute_strategist_first(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    other_index = next(
        (
            index
            for index, task in enumerate(run["task_snapshots"])
            if task["specialist"] == MarketingSpecialistType.ANALYST.value
        ),
        None,
    )
    if other_index is None:
        pytest.skip("Plan has no analyst task")
    response = _execute_specialist(client, auth_headers, project_id, run["id"], other_index)
    assert response.status_code == 409
    assert "not enabled for this role" in response.json()["detail"]


# --- Happy path ---


@pytest.mark.asyncio
async def test_researcher_executes_after_strategist_with_prior_context(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, _strategist_index, researcher_index = _execute_strategist_first(
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
        researcher_index,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.RESEARCHER.value

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "research"
    assert output["title"] == "Audience and market research"
    structured = output["structured_data"]
    assert structured["audience_segments"]
    assert structured["pains"]
    assert structured["desires"]
    assert structured["objections"]
    assert structured["market_assumptions"]
    assert structured["research_gaps"]
    assert structured["recommended_next_questions"]
    assert "raw_response" not in structured
    assert structured.get("mock") is True
    assert any(
        "strategist" in assumption.lower() or "desk research" in assumption.lower()
        for assumption in structured["market_assumptions"]
    )

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
    task_after = run_after["task_snapshots"][researcher_index]
    assert task_after["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    assert task_after["output_ref"] == body["specialist_output_id"]


def test_duplicate_researcher_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, _, researcher_index = _execute_strategist_first(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], researcher_index)
    assert first.status_code == 201
    second = _execute_specialist(client, auth_headers, project_id, run["id"], researcher_index)
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
    run, _, researcher_index = _execute_strategist_first(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        researcher_index,
    )
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
        assert meta.get("tools_metadata") is None or meta.get("tools_metadata", {}).get(
            "available_tool_names",
        ) in (None, [])

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
async def test_ai31_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    strategist_index = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    executed = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        strategist_index,
    )
    assert executed.status_code == 201
    assert executed.json()["specialist"] == MarketingSpecialistType.STRATEGIST.value

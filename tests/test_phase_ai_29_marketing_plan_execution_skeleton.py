"""Phase AI.29 — Marketing plan execution run skeleton."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
)
from app.services.agent_runs import AgentRunService

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.29 Exec"}, headers=headers)
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


def _create_execution_run(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Create gate ---


def test_cannot_create_execution_run_from_draft_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": STRATEGY_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    saved = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=auth_headers,
    ).json()
    response = client.post(
        f"/projects/{project_id}/marketing-plans/{saved['created_resource_id']}/execution-runs",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_approved_plan_creates_queued_run_with_approved_version(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _create_execution_run(client, auth_headers, project_id, plan_id)

    assert run["status"] == "queued"
    plan_row = (
        await db_session.execute(
            select(MarketingPlanTable).where(MarketingPlanTable.id == UUID(plan_id)),
        )
    ).scalar_one()
    assert run["marketing_plan_version_number"] == plan_row.approved_version_number == 1
    assert len(run["task_snapshots"]) >= 1
    assert run["task_snapshots"][0]["status"] == "pending"
    specialists = {t["specialist"] for t in run["task_snapshots"]}
    assert "strategist" in specialists or "content_planner" in specialists


# --- Transitions ---


def test_start_queued_to_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _create_execution_run(client, auth_headers, project_id, plan_id)

    started = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "running"
    assert body["started_at"] is not None


def test_complete_placeholder_running_to_succeeded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _create_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )

    completed = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/complete-placeholder",
        headers=auth_headers,
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "succeeded"
    assert body["result_summary"]["mode"] == "placeholder"
    assert body["result_summary"]["task_count"] == len(body["task_snapshots"])
    assert "Specialist execution is not enabled" in body["result_summary"]["message"]
    assert all(
        t["status"] == MarketingPlanExecutionTaskStatus.PLACEHOLDER_COMPLETED.value
        for t in body["task_snapshots"]
    )
    assert body["finished_at"] is not None


def test_cancel_queued_and_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)

    queued_run = _create_execution_run(client, auth_headers, project_id, plan_id)
    cancelled = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{queued_run['id']}/cancel",
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    running_run = _create_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{running_run['id']}/start",
        headers=auth_headers,
    )
    cancelled_running = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{running_run['id']}/cancel",
        headers=auth_headers,
    )
    assert cancelled_running.status_code == 200
    assert cancelled_running.json()["status"] == "cancelled"


def test_terminal_run_cannot_start_again(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _create_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/cancel",
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    assert response.status_code == 409


# --- Safety ---


@pytest.mark.asyncio
async def test_no_agent_run_children_created(
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
    run = _create_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/complete-placeholder",
        headers=auth_headers,
    )

    after_children = await AgentRunService(db_session).count_children(parent_id, owner_id)
    assert after_children == before_children == 0

    exec_run = (
        await db_session.execute(
            select(MarketingPlanExecutionRunTable).where(
                MarketingPlanExecutionRunTable.id == UUID(run["id"]),
            ),
        )
    ).scalar_one()
    assert exec_run.status == MarketingPlanExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_no_tools_or_llm_on_execution_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _create_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/complete-placeholder",
        headers=auth_headers,
    )

    project_uuid = UUID(project_id)
    tool_count = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolExecutionLogTable)
            .where(ToolExecutionLogTable.project_id == project_uuid),
        )
    ).scalar_one()
    llm_count = (
        await db_session.execute(
            select(func.count())
            .select_from(LLMRequestTable)
            .where(LLMRequestTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0
    assert llm_count == 0


# --- API list/get ---


def test_list_and_get_execution_runs_with_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    created = _create_execution_run(client, auth_headers, project_id, plan_id)

    listed = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs",
        params={"marketing_plan_id": plan_id},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == created["id"] for row in listed.json())

    detail = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{created['id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["marketing_plan_id"] == plan_id


def test_draft_plan_still_blocks_execution_after_ai28_regression(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": STRATEGY_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    save = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=auth_headers,
    ).json()
    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{save['created_resource_id']}",
        headers=auth_headers,
    ).json()
    assert plan["status"] == MarketingPlanStatus.DRAFT.value

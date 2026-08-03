"""Phase AI.35 — Critic specialist dry-run execution."""

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
    "strengths",
    "weaknesses",
    "inconsistencies",
    "missing_information",
    "improvement_actions",
    "approval_recommendation",
)

_APPROVAL_VALUES = frozenset({"approve", "revise", "reject"})


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.35 Critic"}, headers=headers)
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


def _execute_through_copywriter(
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
    ):
        index = _task_index_for(run, specialist)
        response = _execute_specialist(client, headers, project_id, run["id"], index)
        assert response.status_code == 201, response.text
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=headers,
    ).json()
    critic_index = _task_index_for(run_after, MarketingSpecialistType.CRITIC)
    return run_after, critic_index


# --- Gates ---


def test_cannot_execute_before_copywriter(
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
    ):
        index = _task_index_for(run, specialist)
        assert (
            _execute_specialist(client, auth_headers, project_id, run["id"], index).status_code
            == 201
        )
    try:
        critic_index = _task_index_for(run, MarketingSpecialistType.CRITIC)
    except StopIteration:
        pytest.skip("Plan has no critic task")
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        critic_index,
    )
    assert response.status_code == 409
    assert "Copywriter" in response.json()["detail"]


# --- Happy path ---


@pytest.mark.asyncio
async def test_critic_executes_after_full_prior_pipeline(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, critic_index = _execute_through_copywriter(
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
        critic_index,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.CRITIC.value

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "critique"
    assert output["title"] == "Content critique"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    recommendation = structured["approval_recommendation"]
    assert recommendation in _APPROVAL_VALUES
    assert "raw_response" not in structured
    assert structured.get("mock") is True

    for specialist, field in (
        ("strategist", "positioning"),
        ("researcher", "audience_segments"),
        ("content_planner", "post_ideas"),
        ("copywriter", "content_items"),
    ):
        rows = client.get(
            f"/projects/{project_id}/marketing-specialist-outputs",
            params={"execution_run_id": run["id"], "specialist": specialist},
            headers=auth_headers,
        ).json()
        assert rows
        assert rows[0]["structured_data"].get(field)

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
    task_after = run_after["task_snapshots"][critic_index]
    assert task_after["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value


def test_duplicate_critic_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, critic_index = _execute_through_copywriter(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], critic_index)
    assert first.status_code == 201
    second = _execute_specialist(client, auth_headers, project_id, run["id"], critic_index)
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
    run, critic_index = _execute_through_copywriter(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(client, auth_headers, project_id, run["id"], critic_index)
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
async def test_ai31_ai34_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    for specialist, output_type in (
        (MarketingSpecialistType.STRATEGIST, "strategy"),
        (MarketingSpecialistType.RESEARCHER, "research"),
        (MarketingSpecialistType.CONTENT_PLANNER, "content_plan"),
        (MarketingSpecialistType.COPYWRITER, "content_copy"),
    ):
        index = _task_index_for(run, specialist)
        response = _execute_specialist(client, auth_headers, project_id, run["id"], index)
        assert response.status_code == 201, response.text
        detail = client.get(
            f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
            headers=auth_headers,
        ).json()
        assert detail["output_type"] == output_type
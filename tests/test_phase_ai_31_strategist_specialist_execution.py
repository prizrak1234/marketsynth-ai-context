"""Phase AI.31 — Strategist specialist dry-run execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.31 Strategist"}, headers=headers)
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


def _running_run_with_strategist_task(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> tuple[dict, int]:
    run = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert run.status_code == 201, run.text
    body = run.json()
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}/start",
        headers=headers,
    )
    strategist_index = next(
        (
            index
            for index, task in enumerate(body["task_snapshots"])
            if task["specialist"] == MarketingSpecialistType.STRATEGIST.value
        ),
        0,
    )
    refreshed = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}",
        headers=headers,
    ).json()
    return refreshed, strategist_index


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


# --- Gates ---


def test_cannot_execute_if_run_not_running(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    response = _execute_specialist(client, auth_headers, project_id, run["id"], 0)
    assert response.status_code == 409


def test_cannot_execute_non_strategist_task(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, _strategist_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    disabled_specialists: set[str] = set()
    non_strategist_index = next(
        (
            index
            for index, task in enumerate(run["task_snapshots"])
            if task["specialist"] in disabled_specialists
        ),
        None,
    )
    if not disabled_specialists or non_strategist_index is None:
        pytest.skip("All MVP specialists are enabled — no disabled role to assert")
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        non_strategist_index,
    )
    assert response.status_code == 409
    assert "not enabled for this role" in response.json()["detail"]


# --- Happy path ---


@pytest.mark.asyncio
async def test_strategist_execution_creates_output_and_marks_task(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    snapshot = run["task_snapshots"][task_index]
    assert snapshot["specialist"] == MarketingSpecialistType.STRATEGIST.value

    response = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.STRATEGIST.value
    assert body["status"] == MarketingSpecialistOutputStatus.DRAFT.value
    assert body["safe_summary"]

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "strategy"
    assert output["title"] == "Strategic direction"
    assert output["specialist"] == MarketingSpecialistType.STRATEGIST.value
    structured = output["structured_data"]
    assert structured["positioning"]
    assert structured["target_audience"]
    assert structured["key_message"]
    assert "raw_response" not in structured
    assert structured.get("mock") is True

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
    task_after = run_after["task_snapshots"][task_index]
    assert task_after["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    assert task_after["output_ref"] == body["specialist_output_id"]
    assert task_after["safe_notes"] == body["safe_summary"]


def test_duplicate_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert first.status_code == 201
    second = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_uses_approved_plan_version_snapshot(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    plan_row = (
        await db_session.execute(
            select(MarketingPlanTable).where(MarketingPlanTable.id == UUID(plan_id)),
        )
    ).scalar_one()
    approved_version = plan_row.approved_version_number
    assert approved_version is not None

    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    assert run["marketing_plan_version_number"] == approved_version

    executed = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert executed.status_code == 201
    output = (
        await db_session.execute(
            select(MarketingSpecialistOutputTable).where(
                MarketingSpecialistOutputTable.id
                == UUID(executed.json()["specialist_output_id"]),
            ),
        )
    ).scalar_one()
    assert output.marketing_plan_id == UUID(plan_id)


def test_endpoint_ownership_safe(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert executed.status_code == 201

    other = _execute_specialist(
        client,
        other_auth_headers,
        project_id,
        run["id"],
        task_index,
    )
    assert other.status_code == 404


# --- Safety ---


@pytest.mark.asyncio
async def test_no_child_agent_run_tools_or_content_assets(
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
    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    executed = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
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
    llm_count = (
        await db_session.execute(
            select(func.count())
            .select_from(LLMRequestTable)
            .where(LLMRequestTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0
    assert llm_count == 0

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


def test_mock_provider_deterministic_output(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, task_index = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    first = _execute_specialist(client, auth_headers, project_id, run["id"], task_index)
    assert first.status_code == 201
    output_id = first.json()["specialist_output_id"]

    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output_id}/archive",
        headers=auth_headers,
    )
    run2, task_index2 = _running_run_with_strategist_task(
        client,
        auth_headers,
        project_id,
        plan_id,
    )
    second = _execute_specialist(client, auth_headers, project_id, run2["id"], task_index2)
    assert second.status_code == 201
    out2 = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{second.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    out1 = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{output_id}",
        headers=auth_headers,
    ).json()
    assert out1["structured_data"]["positioning"] == out2["structured_data"]["positioning"]
    assert out1["structured_data"]["mock"] is True


@pytest.mark.asyncio
async def test_ai28_ai29_ai30_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    placeholder = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/task-outputs/0/placeholder",
        headers=auth_headers,
    )
    assert placeholder.status_code == 201
    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    ).json()
    assert plan["status"] == MarketingPlanStatus.APPROVED.value

"""Phase AI.30 — Marketing specialist output artifact skeleton."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.marketing_specialist_registry import get_marketing_specialist
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.30 Outputs"}, headers=headers)
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


def _queued_execution_run(
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


def _create_placeholder(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    run_id: str,
    task_index: int,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/task-outputs/{task_index}/placeholder",
        headers=headers,
    )
    return response


# --- Placeholder creation ---


@pytest.mark.asyncio
async def test_placeholder_output_from_execution_run_task_snapshot(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    snapshot = run["task_snapshots"][0]
    specialist = snapshot["specialist"]

    response = _create_placeholder(client, auth_headers, project_id, run["id"], 0)
    assert response.status_code == 201
    body = response.json()

    profile = get_marketing_specialist(MarketingSpecialistType(specialist))
    assert body["specialist"] == specialist
    assert body["task_index"] == 0
    assert body["execution_run_id"] == run["id"]
    assert body["marketing_plan_id"] == plan_id
    assert body["status"] == MarketingSpecialistOutputStatus.DRAFT.value
    assert body["current_version_number"] == 1
    assert body["approved_version_number"] is None
    assert body["title"] == f"{profile.name} output"
    assert body["output_type"] == "placeholder"
    assert "not enabled in this phase" in body["content"]
    assert body["structured_data"]["mode"] == "placeholder"
    assert body["structured_data"]["objective"] == snapshot["objective"]
    assert body["structured_data"]["expected_output"] == snapshot["expected_output"]

    version_count = (
        await db_session.execute(
            select(func.count())
            .select_from(MarketingSpecialistOutputVersionTable)
            .where(
                MarketingSpecialistOutputVersionTable.specialist_output_id == UUID(body["id"]),
            ),
        )
    ).scalar_one()
    assert version_count == 1


def test_invalid_task_index_returns_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    bad_index = len(run["task_snapshots"]) + 5

    response = _create_placeholder(client, auth_headers, project_id, run["id"], bad_index)
    assert response.status_code == 409


def test_duplicate_active_output_returns_existing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)

    first = _create_placeholder(client, auth_headers, project_id, run["id"], 0)
    assert first.status_code == 201
    second = _create_placeholder(client, auth_headers, project_id, run["id"], 0)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_archived_output_blocks_new_placeholder_for_same_task(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)

    created = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()
    archived = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{created['id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200

    retry = _create_placeholder(client, auth_headers, project_id, run["id"], 0)
    assert retry.status_code == 409


# --- Approve / archive ---


def test_approve_sets_approved_version_number(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    output = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()

    approved = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == MarketingSpecialistOutputStatus.APPROVED.value
    assert body["approved_version_number"] == body["current_version_number"] == 1


def test_archive_works_from_draft_and_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)

    draft = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()
    archived_draft = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{draft['id']}/archive",
        headers=auth_headers,
    )
    assert archived_draft.status_code == 200
    assert archived_draft.json()["status"] == MarketingSpecialistOutputStatus.ARCHIVED.value

    if len(run["task_snapshots"]) > 1:
        approved_output = _create_placeholder(
            client,
            auth_headers,
            project_id,
            run["id"],
            1,
        ).json()
    else:
        run2 = _queued_execution_run(client, auth_headers, project_id, plan_id)
        approved_output = _create_placeholder(
            client,
            auth_headers,
            project_id,
            run2["id"],
            0,
        ).json()
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{approved_output['id']}/approve",
        headers=auth_headers,
    )
    archived_approved = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{approved_output['id']}/archive",
        headers=auth_headers,
    )
    assert archived_approved.status_code == 200
    assert archived_approved.json()["status"] == MarketingSpecialistOutputStatus.ARCHIVED.value


def test_archived_cannot_be_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    output = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/archive",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409


# --- API list/get/versions ---


def test_list_get_and_versions_ownership_safe(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    created = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()

    listed = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"]},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert any(row["id"] == created["id"] for row in listed.json())

    detail = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{created['id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200

    versions = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{created['id']}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["version_number"] == 1

    version_one = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{created['id']}/versions/1",
        headers=auth_headers,
    )
    assert version_one.status_code == 200

    other_detail = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{created['id']}",
        headers=other_auth_headers,
    )
    assert other_detail.status_code == 404


def test_complete_placeholder_does_not_auto_create_outputs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/complete-placeholder",
        headers=auth_headers,
    )

    listed = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"]},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []


# --- Safety invariants ---


@pytest.mark.asyncio
async def test_no_child_agent_run_on_placeholder_flow(
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
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    output = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )

    after_children = await AgentRunService(db_session).count_children(parent_id, owner_id)
    assert after_children == before_children == 0


@pytest.mark.asyncio
async def test_no_llm_or_tools_on_placeholder_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    output = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
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


@pytest.mark.asyncio
async def test_approving_output_does_not_create_content_asset(
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
    project_uuid = UUID(project_id)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    output = _create_placeholder(client, auth_headers, project_id, run["id"], 0).json()

    before = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    after = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    assert len(after) == len(before)


@pytest.mark.asyncio
async def test_ai28_ai29_regression_smoke(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Ensure plan approval gate and execution-run skeleton still work."""
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
    draft_blocked = client.post(
        f"/projects/{project_id}/marketing-plans/{save['created_resource_id']}/execution-runs",
        headers=auth_headers,
    )
    assert draft_blocked.status_code == 409

    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _queued_execution_run(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/start",
        headers=auth_headers,
    )
    completed = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}/complete-placeholder",
        headers=auth_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"

    output_rows = (
        await db_session.execute(
            select(func.count()).select_from(MarketingSpecialistOutputTable),
        )
    ).scalar_one()
    assert output_rows == 0

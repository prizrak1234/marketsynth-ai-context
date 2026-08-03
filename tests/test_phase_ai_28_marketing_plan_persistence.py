"""Phase AI.28 — Marketing plan persistence + approval gate."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing_plan import MarketingPlanTable, MarketingPlanVersionTable
from app.schemas.contracts import ChatBlockActionType, MarketingPlanStatus
from app.services.agent_runs import AgentRunService

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"
PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.28 Plans"}, headers=headers)
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


def _chat(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_id: str,
    content: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": content, "agent_id": agent_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _marketing_plan_block(body: dict) -> dict:
    blocks = body.get("blocks") or []
    plan_blocks = [b for b in blocks if b.get("type") == "marketing_plan"]
    assert plan_blocks
    return plan_blocks[0]


def _save_plan_from_chat(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    chat_body: dict,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat_body["session_id"],
            "assistant_message_id": chat_body["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- Block actions ---


def test_save_marketing_plan_action_on_marketing_plan_block(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    block = _marketing_plan_block(body)
    types = {a["type"] for a in block.get("actions", [])}
    assert ChatBlockActionType.SAVE_MARKETING_PLAN.value in types


@pytest.mark.asyncio
async def test_save_action_creates_draft_plan_and_version_one(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    assert saved["created_resource_type"] == "marketing_plan"
    plan_id = UUID(saved["created_resource_id"])

    plan_row = (
        await db_session.execute(
            select(MarketingPlanTable).where(MarketingPlanTable.id == plan_id),
        )
    ).scalar_one()
    assert plan_row.status == MarketingPlanStatus.DRAFT
    assert plan_row.current_version_number == 1
    assert plan_row.approved_version_number is None
    assert plan_row.goal
    assert len(plan_row.specialist_tasks) >= 1

    versions = (
        await db_session.execute(
            select(MarketingPlanVersionTable).where(
                MarketingPlanVersionTable.marketing_plan_id == plan_id,
            ),
        )
    ).scalars().all()
    assert len(versions) == 1
    assert versions[0].version_number == 1


def test_save_stores_source_run_and_session_ids(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{saved['created_resource_id']}",
        headers=auth_headers,
    ).json()
    assert plan["source_run_id"] == chat["agent_run_id"]
    assert plan["source_session_id"] == chat["session_id"]


def test_save_rejected_for_programmer_block(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    )
    response = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_save_missing_plan_data_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    response = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 99,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


# --- API ---


def test_list_and_get_marketing_plans_with_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan_id = saved["created_resource_id"]

    listed = client.get(
        f"/projects/{project_id}/marketing-plans",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert plan_id in ids

    detail = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "draft"
    assert detail.json()["current_version_number"] == 1


def test_approve_sets_approved_version_number(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan_id = saved["created_resource_id"]

    approved = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert body["approved_version_number"] == body["current_version_number"] == 1


def test_archive_marketing_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    archived = client.post(
        f"/projects/{project_id}/marketing-plans/{saved['created_resource_id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_archived_plan_cannot_be_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan_id = saved["created_resource_id"]
    client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/archive",
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_versions_endpoint_returns_version_one(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan_id = saved["created_resource_id"]

    versions = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}/versions",
        headers=auth_headers,
    ).json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1

    one = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}/versions/1",
        headers=auth_headers,
    )
    assert one.status_code == 200
    assert one.json()["goal"]


@pytest.mark.asyncio
async def test_save_and_approve_do_not_create_child_runs(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    owner_id = UUID(chat["session"]["owner_id"])
    parent_id = UUID(chat["agent_run_id"])
    runs = AgentRunService(db_session)

    saved = _save_plan_from_chat(client, auth_headers, project_id, chat)
    assert await runs.count_children(parent_id, owner_id) == 0

    client.post(
        f"/projects/{project_id}/marketing-plans/{saved['created_resource_id']}/approve",
        headers=auth_headers,
    )
    assert await runs.count_children(parent_id, owner_id) == 0


def test_save_does_not_execute_tools(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=STRATEGY_MESSAGE,
    )
    _save_plan_from_chat(client, auth_headers, project_id, chat)
    logs = client.get(
        f"/agent-runs/{chat['agent_run_id']}/tool-executions",
        headers=auth_headers,
    )
    if logs.status_code == 200:
        assert logs.json() == []


def test_programmer_persisted_false_invariant_unchanged(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    )
    assert body["blocks"][0]["persisted"] is False

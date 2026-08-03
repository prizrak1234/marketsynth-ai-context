"""Phase AI.27 — Marketing orchestrator skeleton (planning mode only)."""

from __future__ import annotations

import inspect
import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer import orchestrator_delegation as delegation_module
from app.agents.marketer.marketing_specialist_registry import (
    FORBIDDEN_SPECIALIST_EXECUTION_MARKERS,
    list_marketing_specialists,
)
from app.agents.marketer.planning import (
    build_marketing_execution_plan,
    select_specialists_for_message,
)
from app.agents.marketer import chain_execution as chain_execution_module
from app.schemas.contracts import MarketingExecutionMode, MarketingSpecialistType
from app.services.agent_runs import AgentRunService

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"
LAUNCH_MESSAGE = "Запусти новый продукт"
REWRITE_MESSAGE = "Перепиши этот пост"
ANALYST_MESSAGE = "Проанализируй кампанию"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.27 Marketing"}, headers=headers)
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
    assert plan_blocks, f"expected marketing_plan block, got {[b.get('type') for b in blocks]}"
    return plan_blocks[0]


# --- Registry & contracts ---


def test_marketing_specialist_registry_lists_all_department_roles() -> None:
    profiles = list_marketing_specialists()
    assert len(profiles) == len(MarketingSpecialistType)
    assert {p.specialist_type for p in profiles} == set(MarketingSpecialistType)


def test_frozen_pipeline_registry_subset_still_six_roles() -> None:
    from app.agents.marketer.marketing_specialist_registry import (
        FROZEN_PIPELINE_ORDER,
        list_frozen_pipeline_specialists,
    )

    frozen = list_frozen_pipeline_specialists()
    assert len(frozen) == 6
    assert [p.specialist_type for p in frozen] == list(FROZEN_PIPELINE_ORDER)


def test_build_plan_includes_core_specialists_for_strategy_request() -> None:
    plan = build_marketing_execution_plan(message=STRATEGY_MESSAGE)
    specialists = [task.specialist for task in plan.specialist_tasks]
    assert MarketingSpecialistType.STRATEGIST in specialists
    assert MarketingSpecialistType.RESEARCHER in specialists
    assert MarketingSpecialistType.CONTENT_PLANNER in specialists
    assert MarketingSpecialistType.COPYWRITER in specialists
    assert MarketingSpecialistType.CRITIC in specialists
    assert plan.execution_mode == MarketingExecutionMode.PLANNING


def test_rewrite_request_plan_copywriter_and_critic_only() -> None:
    specialists = select_specialists_for_message(REWRITE_MESSAGE)
    assert specialists == [
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    ]


def test_planning_module_has_no_execution_hooks_in_source() -> None:
    from app.agents.marketer import planning as planning_module

    source = inspect.getsource(planning_module).lower()
    assert "execute_subagent_chain" not in source
    assert "agentruncoordinator" not in source
    for marker in FORBIDDEN_SPECIALIST_EXECUTION_MARKERS:
        assert marker not in source


def test_delegation_routes_to_planning_not_chain_execution() -> None:
    source = inspect.getsource(delegation_module.execute_marketer_orchestrator_delegation)
    assert "execute_marketer_orchestrator_planning" in source
    assert "execute_subagent_chain" not in source


# --- Chat integration ---


def test_orchestrator_chat_returns_marketing_plan_block(
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
    assert block["title"] == "Marketing execution plan"
    assert block["domain"] == "marketing"
    plan = block["data"]["marketing_execution_plan"]
    assert plan["goal"]
    assert len(plan["specialist_tasks"]) >= 4
    specialists = {t["specialist"] for t in plan["specialist_tasks"]}
    assert "strategist" in specialists
    assert "content_planner" in specialists


@pytest.mark.asyncio
async def test_orchestrator_chat_creates_no_child_runs(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=LAUNCH_MESSAGE,
    )
    assert body.get("subagent_chain") is None
    assert body.get("subagent_execution") is None
    owner_id = UUID(body["session"]["owner_id"])
    parent_id = UUID(body["agent_run_id"])
    assert await AgentRunService(db_session).count_children(parent_id, owner_id) == 0


def test_orchestrator_output_has_no_tool_execution(
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
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    output = run.get("output_payload") or {}
    tools = output.get("tools")
    assert tools is None or tools == {}
    assert "marketing_execution_plan" in output
    assert output["marketing_execution_plan"]["execution_mode"] == "planning"


def test_marketing_plan_block_actions_include_save(
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
    action_types = {a["type"] for a in block.get("actions") or []}
    assert "save_marketing_plan" in action_types
    assert "copy_text" in action_types
    assert "export_markdown" in action_types


def test_marketing_plan_block_actions_no_create_asset_on_plan_block(
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
    action_types = {a["type"] for a in block.get("actions") or []}
    assert "create_marketing_asset" not in action_types


def test_assistant_metadata_excludes_full_plan_payload(
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
    metadata = body["assistant_message"]["metadata"]
    blob = json.dumps(metadata).lower()
    assert "specialist_tasks" not in blob
    assert metadata.get("block_types") == ["marketing_plan"]


def test_history_rebuilds_marketing_plan_block(
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
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert assistant["blocks"]
    assert assistant["blocks"][0]["type"] == "marketing_plan"


def test_general_marketing_delegation_planning_no_subagent_chain(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=general_id,
        content=LAUNCH_MESSAGE,
    )
    assert body["general_delegation"]["domain"] == "marketing"
    assert body.get("subagent_chain") is None
    _marketing_plan_block(body)
    marketer_run = client.get(
        f"/agent-runs/{body['general_delegation']['agent_run_id']}",
        headers=auth_headers,
    ).json()
    assert marketer_run["output_payload"].get("marketing_execution_plan")


def test_analyst_phrase_includes_analyst_in_plan(
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
        content=ANALYST_MESSAGE,
    )
    plan = _marketing_plan_block(body)["data"]["marketing_execution_plan"]
    specialists = {t["specialist"] for t in plan["specialist_tasks"]}
    assert "analyst" in specialists


def test_ai_26_programmer_invariant_still_holds(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Regression: AI.27 must not break frozen programmer consultation path."""
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content="Напиши скрипт для webhook",
    )
    assert body["blocks"][0]["persisted"] is False


def test_chain_execution_module_still_exists_for_future_phases() -> None:
    """Subagent chain code remains for AI.28+; chat path does not call it."""
    assert hasattr(chain_execution_module, "execute_subagent_chain")

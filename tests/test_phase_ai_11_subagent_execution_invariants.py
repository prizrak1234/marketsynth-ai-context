"""Phase AI.11.1 — sub-agent execution readiness invariants (freeze guard, updated through AI.15.1)."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import UUID

import pytest
from app.agents.marketer import execution as execution_module
from app.agents.marketer.chain_execution import execute_subagent_chain
from app.agents.marketer.chains import MAX_SUBAGENT_CHAIN_LENGTH
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import (
    SUBAGENT_EXECUTION_SOURCE,
    _MAX_CHILDREN_PER_PARENT,
    _SUPPORTED_SUBAGENTS,
    execute_subagent,
)
from app.agents.marketer.registry import FORBIDDEN_PERSONA_TOOLS, get_subagent
from app.agents.marketer.router import (
    _COPYWRITER_NOUNS,
    _COPYWRITER_PHRASES,
    _COPYWRITER_VERBS,
    _SUBAGENT_PHRASES,
    detect_best_subagent,
    score_copywriter_intent,
)
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.schemas.agent_chat import AgentChatSendResponse, AgentChatSubagentExecution
from app.schemas.contracts import AgentRun
from app.services import agent_chat_service as agent_chat_service_module
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

NATURAL_COPYWRITER_MESSAGE = "Перепиши этот пост"
CONTENT_PLAN_MESSAGE = "Сделай контент-план"

# Persona-only (router may select; no child execution).
PERSONA_ONLY_SUBAGENTS = frozenset({MarketerSubAgentType.ANALYST})

SUPPORTED_EXECUTION_SUBAGENTS = frozenset(
    {
        MarketerSubAgentType.COPYWRITER,
        MarketerSubAgentType.RESEARCHER,
        MarketerSubAgentType.STRATEGIST,
    },
)

EXECUTION_FORBIDDEN_TOOLS = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)

EXECUTION_SOURCE_FORBIDDEN_MARKERS = (
    "langgraph",
    "handoff",
    "parallel_execution",
    "swarm",
)

@pytest.fixture
def persona_write_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in (
        "AGENT_WRITE_TOOLS_ENABLED",
        "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
        "CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.11.1 Invariants"}, headers=headers)
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


def test_invariant_perepishi_etot_post_routes_to_copywriter() -> None:
    assert detect_best_subagent(message=NATURAL_COPYWRITER_MESSAGE) == MarketerSubAgentType.COPYWRITER
    assert score_copywriter_intent("перепиши этот пост") >= 12


def test_invariant_copywriter_router_covers_natural_speech_tokens() -> None:
    for token in ("перепиши", "переписать", "улучши", "улучшить", "rewrite", "improve"):
        assert any(token in phrase for phrase in _COPYWRITER_PHRASES) or token in _COPYWRITER_VERBS
    for token in ("пост", "текст", "copy"):
        assert token in _COPYWRITER_NOUNS
    assert "сделай текст" in _COPYWRITER_PHRASES


def test_invariant_supported_subagents_copywriter_researcher_strategist() -> None:
    assert _SUPPORTED_SUBAGENTS == SUPPORTED_EXECUTION_SUBAGENTS


def test_invariant_legacy_execute_subagent_max_one_child_constant() -> None:
    assert _MAX_CHILDREN_PER_PARENT == 1


def test_invariant_chain_execution_module_exists() -> None:
    assert MAX_SUBAGENT_CHAIN_LENGTH == 3
    assert "run_subagent_child" in inspect.getsource(execute_subagent_chain)


def test_invariant_agent_run_contract_has_parent_field() -> None:
    assert "parent_agent_run_id" in AgentRun.model_fields


def test_invariant_chat_response_has_subagent_execution_field() -> None:
    assert "subagent_execution" in AgentChatSendResponse.model_fields
    assert "subagent" in AgentChatSubagentExecution.model_fields
    assert "agent_run_id" in AgentChatSubagentExecution.model_fields


def test_invariant_execution_module_no_langgraph_or_handoff() -> None:
    source = inspect.getsource(execution_module).lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in source


def test_invariant_orchestrator_delegation_in_chat_service() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    assert "execute_marketer_orchestrator_delegation" in source
    assert "execute_general_agent" in source
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "handoff" not in lowered


def test_invariant_analyst_router_sample() -> None:
    assert detect_best_subagent(message="Проанализируй кампанию") == MarketerSubAgentType.ANALYST


def test_invariant_strategist_and_researcher_router_samples() -> None:
    assert detect_best_subagent(message=CONTENT_PLAN_MESSAGE) == MarketerSubAgentType.STRATEGIST
    assert detect_best_subagent(message="Исследуй аудиторию") == MarketerSubAgentType.RESEARCHER


def test_invariant_copywriter_persona_forbids_approve_publish_schedule() -> None:
    profile = get_subagent(MarketerSubAgentType.COPYWRITER)
    assert profile.allowed_tools.isdisjoint(FORBIDDEN_PERSONA_TOOLS)
    assert profile.allowed_tools.isdisjoint(EXECUTION_FORBIDDEN_TOOLS)


def test_invariant_copywriter_allowed_tools_subset_of_agent_profile(
    persona_write_flags_on: None,
) -> None:
    profile = get_subagent(MarketerSubAgentType.COPYWRITER)
    agent_allowlist = get_agent_tool_allowlist(profile.mapped_agent_type)
    assert profile.allowed_tools <= agent_allowlist


def test_invariant_registry_still_lists_all_four_subagent_types() -> None:
    assert set(_SUBAGENT_PHRASES.keys()) == set(MarketerSubAgentType)


def test_invariant_orchestrator_chat_creates_parent_and_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    copywriter_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="copywriter",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_COPYWRITER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["subagent_execution"]["subagent"] == "copywriter"

    parent_id = body["agent_run_id"]
    child_id = body["subagent_execution"]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()

    assert parent["parent_agent_run_id"] is None
    assert parent["agent_id"] == orchestrator_id
    assert child["parent_agent_run_id"] == parent_id
    assert child["agent_id"] == copywriter_id
    assert child["project_id"] == parent["project_id"]


def test_invariant_analyst_route_does_not_spawn_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Проанализируй кампанию", "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("subagent_execution") is None
    assert body.get("subagent_chain") is None


def test_invariant_content_plan_returns_marketing_execution_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": CONTENT_PLAN_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("subagent_chain") is None
    plan_blocks = [b for b in body.get("blocks", []) if b.get("type") == "marketing_plan"]
    assert plan_blocks
    specialists = {
        t["specialist"]
        for t in plan_blocks[0]["data"]["marketing_execution_plan"]["specialist_tasks"]
    }
    assert "strategist" in specialists
    assert "content_planner" in specialists


@pytest.mark.skip(reason="AI.27: chat planning mode does not create copywriter child runs")
@pytest.mark.asyncio
async def test_invariant_no_nesting_subagent_execution(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_COPYWRITER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    child_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["subagent_execution"]["agent_run_id"]),
    )
    assert child_run is not None

    with pytest.raises(InvalidStateError, match="Only orchestrator"):
        await execute_subagent(
            db_session,
            parent_run=child_run,
            subagent_type=MarketerSubAgentType.COPYWRITER,
            input_payload={"prompt": "nested"},
            owner_id=owner_id,
        )


@pytest.mark.skip(reason="AI.27: chat planning mode does not create copywriter child runs")
@pytest.mark.asyncio
async def test_invariant_legacy_execute_subagent_rejects_second_child(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_COPYWRITER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    parent_id = UUID(sent["agent_run_id"])
    parent_run = await AgentRunService(db_session).get_run(owner_id, parent_id)
    assert parent_run is not None

    assert await AgentRunService(db_session).count_children(parent_id, owner_id) == 1

    with pytest.raises(InvalidStateError, match="already has"):
        await execute_subagent(
            db_session,
            parent_run=parent_run,
            subagent_type=MarketerSubAgentType.COPYWRITER,
            input_payload={"prompt": "second child"},
            owner_id=owner_id,
        )


@pytest.mark.parametrize(
    "subagent_type",
    sorted(PERSONA_ONLY_SUBAGENTS, key=lambda t: t.value),
)
def test_invariant_persona_only_not_supported_for_execution(
    subagent_type: MarketerSubAgentType,
) -> None:
    assert subagent_type not in _SUPPORTED_SUBAGENTS


def test_invariant_subagent_execution_source_constant() -> None:
    assert SUBAGENT_EXECUTION_SOURCE == "subagent_execution"


def test_invariant_no_subagent_execution_tools_in_registry() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for name in ("marketer_subagent.run", "subagent.execute", "orchestrator.delegate"):
        assert name not in registered

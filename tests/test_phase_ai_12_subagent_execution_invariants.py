"""Phase AI.12.1 — researcher execution freeze invariants (guard, updated through AI.15.1)."""

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
from app.agents.marketer.router import detect_best_subagent
from app.core.exceptions import InvalidStateError
from app.schemas.agent_chat import AgentChatSendResponse, AgentChatSubagentExecution
from app.services import agent_chat_service as agent_chat_service_module
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
)
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

NATURAL_COPYWRITER_MESSAGE = "Перепиши этот пост"
NATURAL_RESEARCHER_MESSAGE = "Исследуй аудиторию"
AMBIGUOUS_MARKET_MESSAGE = "Проанализируй рынок"

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
        "content_asset.archive",
        "publication_job.create",
        "publication_job.schedule",
    },
)

RESEARCHER_FORBIDDEN_WRITE_TOOLS = frozenset(
    {
        CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
        CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
        "content_asset.create",
        "campaign_plan_draft.create",
    },
)

EXECUTION_SOURCE_FORBIDDEN_MARKERS = (
    "langgraph",
    "handoff",
    "parallel_execution",
    "swarm",
)

MARKETER_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.12.1 Invariants"}, headers=headers)
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


# --- Supported sub-agents ---


def test_invariant_supported_subagents_copywriter_researcher_strategist() -> None:
    assert _SUPPORTED_SUBAGENTS == SUPPORTED_EXECUTION_SUBAGENTS


@pytest.mark.parametrize(
    "subagent_type",
    sorted(PERSONA_ONLY_SUBAGENTS, key=lambda t: t.value),
)
def test_invariant_persona_only_not_supported_for_execution(
    subagent_type: MarketerSubAgentType,
) -> None:
    assert subagent_type not in _SUPPORTED_SUBAGENTS


def test_invariant_chain_execution_available() -> None:
    assert MAX_SUBAGENT_CHAIN_LENGTH == 3
    assert "run_subagent_child" in inspect.getsource(execute_subagent_chain)


# --- Router (frozen routing table) ---


def test_invariant_issleduy_auditoriyu_routes_to_researcher() -> None:
    assert detect_best_subagent(message=NATURAL_RESEARCHER_MESSAGE) == MarketerSubAgentType.RESEARCHER


def test_invariant_perepishi_etot_post_routes_to_copywriter() -> None:
    assert detect_best_subagent(message=NATURAL_COPYWRITER_MESSAGE) == MarketerSubAgentType.COPYWRITER


def test_invariant_proanaliziruy_rynok_routes_to_none_not_researcher_or_analyst() -> None:
    """Frozen disambiguation: no phrase match → orchestrator, no child (see audit doc)."""
    assert detect_best_subagent(message=AMBIGUOUS_MARKET_MESSAGE) is None


def test_invariant_proanaliziruy_kampaniyu_routes_to_analyst_persona_only() -> None:
    assert detect_best_subagent(message="Проанализируй кампанию") == MarketerSubAgentType.ANALYST


@pytest.mark.parametrize(
    ("message", "expected_subagent"),
    [
        ("Проанализируй кампанию", "analyst"),
        (AMBIGUOUS_MARKET_MESSAGE, None),
    ],
)
def test_invariant_non_execution_routes_do_not_spawn_child(
    client: TestClient,
    auth_headers: dict[str, str],
    message: str,
    expected_subagent: str | None,
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
        json={"content": message, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("subagent_execution") is None
    routed = detect_best_subagent(message=message)
    if expected_subagent is None:
        assert routed is None
    else:
        assert routed is not None
        assert routed.value == expected_subagent


# --- Chat delegate path ---


def test_invariant_orchestrator_delegation_in_chat_service() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    assert "execute_marketer_orchestrator_delegation" in source
    assert "execute_general_agent" in source
    assert "AgentType.ORCHESTRATOR" in source
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "handoff" not in lowered


def test_invariant_chat_response_has_subagent_execution_field() -> None:
    assert "subagent_execution" in AgentChatSendResponse.model_fields
    assert "subagent" in AgentChatSubagentExecution.model_fields
    assert "agent_run_id" in AgentChatSubagentExecution.model_fields


def test_invariant_subagent_execution_source_constant() -> None:
    assert SUBAGENT_EXECUTION_SOURCE == "subagent_execution"


def test_invariant_execution_module_no_langgraph_or_handoff() -> None:
    source = inspect.getsource(execution_module).lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in source


def test_invariant_marketer_package_no_langgraph_or_handoff_imports() -> None:
    combined = ""
    for path in MARKETER_DIR.glob("*.py"):
        combined += path.read_text(encoding="utf-8") + "\n"
    lowered = combined.lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in lowered


def test_invariant_no_subagent_execution_tools_in_registry() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for name in ("marketer_subagent.run", "subagent.execute", "orchestrator.delegate"):
        assert name not in registered


# --- Researcher persona / tools ---


def test_invariant_researcher_persona_forbids_approve_publish_schedule_archive() -> None:
    profile = get_subagent(MarketerSubAgentType.RESEARCHER)
    assert profile.allowed_tools.isdisjoint(FORBIDDEN_PERSONA_TOOLS)
    assert profile.allowed_tools.isdisjoint(EXECUTION_FORBIDDEN_TOOLS)


def test_invariant_researcher_persona_has_no_write_tools() -> None:
    profile = get_subagent(MarketerSubAgentType.RESEARCHER)
    assert profile.allowed_tools.isdisjoint(RESEARCHER_FORBIDDEN_WRITE_TOOLS)


def test_invariant_researcher_allowed_tools_subset_of_agent_profile() -> None:
    profile = get_subagent(MarketerSubAgentType.RESEARCHER)
    agent_allowlist = get_agent_tool_allowlist(profile.mapped_agent_type)
    assert profile.allowed_tools <= agent_allowlist


# --- Integration: researcher child ---


def test_invariant_orchestrator_chat_creates_parent_and_researcher_child(
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
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_RESEARCHER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["subagent_execution"]["subagent"] == "researcher"

    parent_id = body["agent_run_id"]
    child_id = body["subagent_execution"]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()

    assert parent["parent_agent_run_id"] is None
    assert parent["agent_id"] == orchestrator_id
    assert child["parent_agent_run_id"] == parent_id
    assert child["agent_id"] == researcher_id
    assert child["input_payload"].get("source") == SUBAGENT_EXECUTION_SOURCE
    assert body["assistant_message"]["agent_run_id"] == child_id


def test_invariant_copywriter_execution_still_works_after_researcher(
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
    child = client.get(
        f"/agent-runs/{body['subagent_execution']['agent_run_id']}",
        headers=auth_headers,
    ).json()
    assert child["agent_id"] == copywriter_id
    assert child["parent_agent_run_id"] == body["agent_run_id"]


def test_invariant_legacy_execute_subagent_max_one_child_constant() -> None:
    assert _MAX_CHILDREN_PER_PARENT == 1


@pytest.mark.asyncio
async def test_invariant_legacy_execute_subagent_rejects_second_researcher_child(
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
    _create_agent(client, auth_headers, project_id, agent_type="researcher")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_RESEARCHER_MESSAGE, "agent_id": orchestrator_id},
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
            subagent_type=MarketerSubAgentType.RESEARCHER,
            input_payload={"prompt": "second child"},
            owner_id=owner_id,
        )


@pytest.mark.asyncio
async def test_invariant_researcher_child_cannot_spawn_nested_subagent(
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
    _create_agent(client, auth_headers, project_id, agent_type="researcher")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_RESEARCHER_MESSAGE, "agent_id": orchestrator_id},
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
            subagent_type=MarketerSubAgentType.RESEARCHER,
            input_payload={"prompt": "nested"},
            owner_id=owner_id,
        )

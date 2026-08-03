"""Phase AI.13.1 — strategist execution freeze invariants (guard, updated through AI.15.1)."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import UUID

import pytest
from app.agents.marketer import execution as execution_module
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import (
    SUBAGENT_EXECUTION_SOURCE,
    _MAX_CHILDREN_PER_PARENT,
    _SUPPORTED_SUBAGENTS,
    execute_subagent,
)
from app.agents.marketer.registry import FORBIDDEN_PERSONA_TOOLS, get_subagent
from app.agents.marketer.router import _SUBAGENT_PHRASES, detect_best_subagent
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.schemas.agent_chat import AgentChatSendResponse, AgentChatSubagentExecution
from app.schemas.contracts import AgentType
from app.services import agent_chat_service as agent_chat_service_module
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

NATURAL_STRATEGIST_CONTENT_PLAN = "Сделай контент-план"
NATURAL_STRATEGIST_LAUNCH = "Разработай стратегию запуска"
POSITIONING_MESSAGE = "Нужно позиционирование для продукта"
OFFER_MESSAGE = "Предложи оффер для лендинга"
NATURAL_COPYWRITER_MESSAGE = "Перепиши этот пост"
NATURAL_RESEARCHER_MESSAGE = "Исследуй аудиторию"
AMBIGUOUS_MARKET_MESSAGE = "Проанализируй рынок"

NON_EXECUTION_SUBAGENTS = frozenset({MarketerSubAgentType.ANALYST})

FROZEN_STRATEGIST_PHRASES = (
    "сделай контент-план",
    "создай контент-план",
    "разработай стратегию",
    "стратегия запуска",
    "позиционирование",
    "оффер",
    "план кампании",
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

EXECUTION_SOURCE_FORBIDDEN_MARKERS = (
    "langgraph",
    "handoff",
    "parallel_execution",
    "swarm",
)

MARKETER_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer"


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
    response = client.post("/projects", json={"name": "AI.13.1 Invariants"}, headers=headers)
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


def test_invariant_three_child_agents_in_supported_subagents() -> None:
    assert _SUPPORTED_SUBAGENTS == frozenset(
        {
            MarketerSubAgentType.COPYWRITER,
            MarketerSubAgentType.RESEARCHER,
            MarketerSubAgentType.STRATEGIST,
        },
    )


def test_invariant_analyst_not_supported_for_execution() -> None:
    assert MarketerSubAgentType.ANALYST not in _SUPPORTED_SUBAGENTS


def test_invariant_frozen_strategist_phrases_in_router() -> None:
    router_phrases = _SUBAGENT_PHRASES[MarketerSubAgentType.STRATEGIST]
    for phrase in FROZEN_STRATEGIST_PHRASES:
        assert phrase in router_phrases


# --- Router ---


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (NATURAL_STRATEGIST_CONTENT_PLAN, MarketerSubAgentType.STRATEGIST),
        (NATURAL_STRATEGIST_LAUNCH, MarketerSubAgentType.STRATEGIST),
        (POSITIONING_MESSAGE, MarketerSubAgentType.STRATEGIST),
        (OFFER_MESSAGE, MarketerSubAgentType.STRATEGIST),
    ],
)
def test_invariant_strategist_phrases_route_to_strategist(
    message: str,
    expected: MarketerSubAgentType,
) -> None:
    assert detect_best_subagent(message=message) == expected


def test_invariant_proanaliziruy_rynok_routes_to_none() -> None:
    assert detect_best_subagent(message=AMBIGUOUS_MARKET_MESSAGE) is None


def test_invariant_proanaliziruy_kampaniyu_routes_to_analyst_persona_only() -> None:
    assert detect_best_subagent(message="Проанализируй кампанию") == MarketerSubAgentType.ANALYST


# --- Execution layer guards ---


def test_invariant_orchestrator_delegation_in_chat_service() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    assert "execute_marketer_orchestrator_delegation" in source
    assert "resolve_execution_chain" not in source
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "handoff" not in lowered


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


def test_invariant_max_one_child_per_parent_constant() -> None:
    assert _MAX_CHILDREN_PER_PARENT == 1


def test_invariant_subagent_execution_source_constant() -> None:
    assert SUBAGENT_EXECUTION_SOURCE == "subagent_execution"


def test_invariant_chat_response_has_subagent_execution_field() -> None:
    assert "subagent_execution" in AgentChatSendResponse.model_fields
    assert "subagent" in AgentChatSubagentExecution.model_fields
    assert "agent_run_id" in AgentChatSubagentExecution.model_fields


# --- Strategist persona / tools ---


def test_invariant_strategist_persona_forbids_approve_publish_schedule_archive() -> None:
    profile = get_subagent(MarketerSubAgentType.STRATEGIST)
    assert profile.allowed_tools.isdisjoint(FORBIDDEN_PERSONA_TOOLS)
    assert profile.allowed_tools.isdisjoint(EXECUTION_FORBIDDEN_TOOLS)


def test_invariant_strategist_allowed_tools_subset_of_agent_profile(
    persona_write_flags_on: None,
) -> None:
    profile = get_subagent(MarketerSubAgentType.STRATEGIST)
    agent_allowlist = get_agent_tool_allowlist(profile.mapped_agent_type)
    assert profile.allowed_tools <= agent_allowlist
    assert profile.mapped_agent_type == AgentType.STRATEGIST


# --- Integration: strategist child ---


def test_invariant_orchestrator_chat_creates_parent_and_strategist_child(
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
    strategist_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="strategist",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": POSITIONING_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["subagent_execution"]["subagent"] == "strategist"
    assert body.get("subagent_chain") is None or len(body["subagent_chain"]) == 1

    parent_id = body["agent_run_id"]
    child_id = body["subagent_execution"]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()

    assert parent["parent_agent_run_id"] is None
    assert parent["agent_id"] == orchestrator_id
    assert child["parent_agent_run_id"] == parent_id
    assert child["agent_id"] == strategist_id
    assert child["input_payload"].get("source") == SUBAGENT_EXECUTION_SOURCE

    strategist_agent = client.get(f"/agents/{strategist_id}", headers=auth_headers).json()
    assert strategist_agent["type"] == AgentType.STRATEGIST.value


def test_invariant_copywriter_and_researcher_regression(
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
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")

    copy_body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_COPYWRITER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    assert copy_body.get("subagent_execution") is None
    copy_plan = next(
        b for b in copy_body.get("blocks", []) if b.get("type") == "marketing_plan"
    )
    copy_specialists = {
        t["specialist"]
        for t in copy_plan["data"]["marketing_execution_plan"]["specialist_tasks"]
    }
    assert "copywriter" in copy_specialists

    research_body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_RESEARCHER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    assert research_body.get("subagent_execution") is None
    research_plan = next(
        b for b in research_body.get("blocks", []) if b.get("type") == "marketing_plan"
    )
    research_specialists = {
        t["specialist"]
        for t in research_plan["data"]["marketing_execution_plan"]["specialist_tasks"]
    }
    assert "researcher" in research_specialists


@pytest.mark.parametrize(
    ("message", "expected_router"),
    [
        ("Проанализируй кампанию", "analyst"),
        (AMBIGUOUS_MARKET_MESSAGE, None),
    ],
)
def test_invariant_analyst_and_ambiguous_market_no_child(
    client: TestClient,
    auth_headers: dict[str, str],
    message: str,
    expected_router: str | None,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
    )
    _create_agent(client, auth_headers, project_id, agent_type="strategist")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": message, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("subagent_execution") is None
    routed = detect_best_subagent(message=message)
    if expected_router is None:
        assert routed is None
    else:
        assert routed is not None
        assert routed.value == expected_router


@pytest.mark.skip(reason="AI.27: chat planning mode does not create strategist child runs")
@pytest.mark.asyncio
async def test_invariant_legacy_execute_subagent_rejects_second_strategist_child(
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
    _create_agent(client, auth_headers, project_id, agent_type="strategist")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": POSITIONING_MESSAGE, "agent_id": orchestrator_id},
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
            subagent_type=MarketerSubAgentType.STRATEGIST,
            input_payload={"prompt": "second child"},
            owner_id=owner_id,
        )


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
        json={"content": NATURAL_STRATEGIST_CONTENT_PLAN, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("subagent_chain") is None
    plan_block = next(b for b in body.get("blocks", []) if b.get("type") == "marketing_plan")
    specialists = {
        t["specialist"]
        for t in plan_block["data"]["marketing_execution_plan"]["specialist_tasks"]
    }
    assert "strategist" in specialists
    assert "copywriter" in specialists


@pytest.mark.skip(reason="AI.27: chat planning mode does not create strategist child runs")
@pytest.mark.asyncio
async def test_invariant_strategist_child_cannot_spawn_nested_subagent(
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
    _create_agent(client, auth_headers, project_id, agent_type="strategist")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_STRATEGIST_LAUNCH, "agent_id": orchestrator_id},
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
            subagent_type=MarketerSubAgentType.STRATEGIST,
            input_payload={"prompt": "nested"},
            owner_id=owner_id,
        )

"""Phase AI.13 — orchestrator → strategist sub-agent execution (integration).

Freeze guard: tests/test_phase_ai_13_strategist_execution_invariants.py (AI.13.1).
"""

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
from app.agents.marketer.router import detect_best_subagent
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from fastapi.testclient import TestClient

NATURAL_STRATEGIST_CONTENT_PLAN = "Сделай контент-план"
NATURAL_STRATEGIST_LAUNCH = "Разработай стратегию запуска"
NATURAL_COPYWRITER_MESSAGE = "Перепиши этот пост"
NATURAL_RESEARCHER_MESSAGE = "Исследуй аудиторию"
AMBIGUOUS_MARKET_MESSAGE = "Проанализируй рынок"

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


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Strategist Exec") -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
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


def test_supported_subagents_includes_strategist() -> None:
    assert MarketerSubAgentType.STRATEGIST in _SUPPORTED_SUBAGENTS
    assert MarketerSubAgentType.COPYWRITER in _SUPPORTED_SUBAGENTS
    assert MarketerSubAgentType.RESEARCHER in _SUPPORTED_SUBAGENTS
    assert MarketerSubAgentType.ANALYST not in _SUPPORTED_SUBAGENTS


def test_router_sdelaj_kontent_plan_to_strategist() -> None:
    assert detect_best_subagent(message=NATURAL_STRATEGIST_CONTENT_PLAN) == MarketerSubAgentType.STRATEGIST


def test_router_razrabotaj_strategiyu_zapuska_to_strategist() -> None:
    assert detect_best_subagent(message=NATURAL_STRATEGIST_LAUNCH) == MarketerSubAgentType.STRATEGIST


def test_router_proanaliziruy_rynok_still_none() -> None:
    assert detect_best_subagent(message=AMBIGUOUS_MARKET_MESSAGE) is None


def test_orchestrator_delegates_strategist_child_run(
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

    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_STRATEGIST_CONTENT_PLAN, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert [s["subagent"] for s in body["subagent_chain"]] == ["strategist", "copywriter"]
    assert body["subagent_execution"]["subagent"] == "copywriter"

    parent_id = body["agent_run_id"]
    strategist_child_id = body["subagent_chain"][0]["agent_run_id"]
    final_child_id = body["subagent_execution"]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    strategist_child = client.get(
        f"/agent-runs/{strategist_child_id}",
        headers=auth_headers,
    ).json()

    assert parent["parent_agent_run_id"] is None
    assert parent["agent_id"] == orchestrator_id
    assert strategist_child["parent_agent_run_id"] == parent_id
    assert strategist_child["agent_id"] == strategist_id
    assert strategist_child["status"] == "succeeded"
    assert strategist_child["input_payload"].get("source") == SUBAGENT_EXECUTION_SOURCE
    assert body["assistant_message"]["agent_run_id"] == final_child_id

    strategist_agent = client.get(f"/agents/{strategist_id}", headers=auth_headers).json()
    assert strategist_agent["type"] == AgentType.STRATEGIST.value


def test_orchestrator_delegates_strategist_for_launch_strategy_phrase(
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

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_STRATEGIST_LAUNCH, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["subagent_execution"]["subagent"] == "strategist"


def test_copywriter_and_researcher_execution_still_work(
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

    copy_sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_COPYWRITER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert copy_sent.json()["subagent_chain"][0]["subagent"] == "copywriter"

    research_sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_RESEARCHER_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert research_sent.json()["subagent_chain"][0]["subagent"] == "researcher"


def test_analyst_route_does_not_spawn_child(
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
    assert sent.json().get("subagent_execution") is None


def test_ambiguous_market_message_no_subagent_execution(
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
        json={"content": AMBIGUOUS_MARKET_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("subagent_execution") is None


def test_strategist_persona_forbids_approve_publish_schedule_archive() -> None:
    profile = get_subagent(MarketerSubAgentType.STRATEGIST)
    assert profile.allowed_tools.isdisjoint(FORBIDDEN_PERSONA_TOOLS)
    assert profile.allowed_tools.isdisjoint(EXECUTION_FORBIDDEN_TOOLS)


def test_strategist_allowed_tools_subset_of_agent_profile(
    persona_write_flags_on: None,
) -> None:
    profile = get_subagent(MarketerSubAgentType.STRATEGIST)
    agent_allowlist = get_agent_tool_allowlist(profile.mapped_agent_type)
    assert profile.allowed_tools <= agent_allowlist


def test_strategist_child_tool_executions_avoid_forbidden_tools(
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
    ).json()
    child_id = UUID(sent["subagent_chain"][-1]["agent_run_id"])

    logs = client.get(f"/agent-runs/{child_id}/tool-executions", headers=auth_headers)
    if logs.status_code == 200 and logs.json():
        profile = get_subagent(MarketerSubAgentType.STRATEGIST)
        for entry in logs.json():
            tool_name = entry.get("tool_name") or entry.get("name")
            if tool_name:
                assert tool_name in profile.allowed_tools or tool_name not in EXECUTION_FORBIDDEN_TOOLS


def test_execution_module_no_langgraph_handoff_parallel() -> None:
    source = inspect.getsource(execution_module).lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in source


def test_marketer_package_no_langgraph_handoff_parallel() -> None:
    paths = (
        MARKETER_DIR / "execution.py",
        MARKETER_DIR / "chain_execution.py",
        MARKETER_DIR / "router.py",
    )
    combined = "".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in combined


def test_max_one_child_per_parent_constant() -> None:
    assert _MAX_CHILDREN_PER_PARENT == 1


@pytest.mark.skip(reason="AI.14 allows up to 3 sibling children; see test_subagent_chain_execution")
@pytest.mark.asyncio
async def test_only_one_child_per_parent_strategist_path(
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
        json={"content": NATURAL_STRATEGIST_CONTENT_PLAN, "agent_id": orchestrator_id},
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


@pytest.mark.asyncio
async def test_strategist_child_cannot_spawn_nested_subagent(
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

    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_STRATEGIST_CONTENT_PLAN, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    child_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["subagent_chain"][0]["agent_run_id"]),
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


def test_direct_strategist_chat_skips_subagent_execution(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    strategist_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="strategist",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": NATURAL_STRATEGIST_CONTENT_PLAN, "agent_id": strategist_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("subagent_execution") is None

"""Phase AI.14 — sequential multi-subagent chain execution."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from uuid import UUID

import pytest
from app.agents.marketer.chain_execution import execute_subagent_chain
from app.agents.marketer.chains import (
    COMPACT_SUBAGENT_OUTPUT_MAX_BYTES,
    CONTENT_LAUNCH,
    CONTENT_PLAN,
    MAX_SUBAGENT_CHAIN_LENGTH,
    RESEARCH,
    REWRITE,
)
from app.agents.marketer.compact_output import compact_subagent_output
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import SUBAGENT_EXECUTION_SOURCE, execute_subagent, run_subagent_child
from app.agents.marketer.registry import FORBIDDEN_PERSONA_TOOLS, get_subagent
from app.agents.marketer.router import detect_execution_chain, resolve_execution_chain
from app.core.exceptions import InvalidStateError
from app.services.agent_runs import AgentRunService
from fastapi.testclient import TestClient

MARKETER_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer"

LAUNCH_MESSAGE = "Запусти новый продукт"
CONTENT_PLAN_MESSAGE = "Сделай контент-план"
REWRITE_MESSAGE = "Перепиши этот пост"
RESEARCH_MESSAGE = "Исследуй аудиторию"
AMBIGUOUS_MARKET_MESSAGE = "Проанализируй рынок"

FORBIDDEN_MARKERS = ("langgraph", "handoff", "parallel_execution", "swarm")

_SKIP_AI27_CHAT = pytest.mark.skip(
    reason="AI.27: agent-chat uses marketing planning mode, not subagent chains",
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chain Project"}, headers=headers)
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


def test_detect_launch_chain() -> None:
    assert detect_execution_chain(message=LAUNCH_MESSAGE) == CONTENT_LAUNCH


def test_detect_content_plan_chain() -> None:
    assert detect_execution_chain(message=CONTENT_PLAN_MESSAGE) == CONTENT_PLAN


def test_detect_rewrite_chain() -> None:
    assert detect_execution_chain(message=REWRITE_MESSAGE) == REWRITE


def test_detect_research_chain() -> None:
    assert detect_execution_chain(message=RESEARCH_MESSAGE) == RESEARCH


def test_proanaliziruy_rynok_chain_none() -> None:
    assert detect_execution_chain(message=AMBIGUOUS_MARKET_MESSAGE) is None
    assert resolve_execution_chain(message=AMBIGUOUS_MARKET_MESSAGE) is None


def test_max_chain_length_constant() -> None:
    assert MAX_SUBAGENT_CHAIN_LENGTH == 3
    assert len(CONTENT_LAUNCH) == 3


def test_compact_subagent_output_within_limit() -> None:
    large = {"content": "x" * 8000, "tools": {"tool_names": ["a"] * 50}}
    compact = compact_subagent_output(large)
    assert len(json.dumps(compact, ensure_ascii=False).encode("utf-8")) <= COMPACT_SUBAGENT_OUTPUT_MAX_BYTES


def test_marketer_chain_modules_no_langgraph_handoff() -> None:
    paths = (
        MARKETER_DIR / "execution.py",
        MARKETER_DIR / "chain_execution.py",
        MARKETER_DIR / "router.py",
        MARKETER_DIR / "chains.py",
    )
    combined = "".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in combined


@_SKIP_AI27_CHAT
def test_launch_chain_creates_three_sibling_children(
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
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": LAUNCH_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    chain = body["subagent_chain"]
    assert chain is not None
    assert [entry["subagent"] for entry in chain] == ["researcher", "strategist", "copywriter"]
    for entry in chain:
        assert entry.get("status") == "succeeded"
    assert body["subagent_execution"]["subagent"] == "copywriter"

    parent_id = body["agent_run_id"]
    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    assert parent["parent_agent_run_id"] is None

    child_ids = [entry["agent_run_id"] for entry in chain]
    for child_id in child_ids:
        child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
        assert child["parent_agent_run_id"] == parent_id
        assert child["input_payload"].get("source") == SUBAGENT_EXECUTION_SOURCE

    assert len(child_ids) == len(set(child_ids))


@_SKIP_AI27_CHAT
def test_content_plan_chain_strategist_then_copywriter(
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
    chain = sent.json()["subagent_chain"]
    assert [entry["subagent"] for entry in chain] == ["strategist", "copywriter"]


@_SKIP_AI27_CHAT
def test_rewrite_chain_copywriter_only(
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

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": REWRITE_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    chain = sent.json()["subagent_chain"]
    assert len(chain) == 1
    assert chain[0]["subagent"] == "copywriter"


@_SKIP_AI27_CHAT
def test_research_chain_researcher_only(
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
    _create_agent(client, auth_headers, project_id, agent_type="researcher")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": RESEARCH_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["subagent_chain"][0]["subagent"] == "researcher"


@_SKIP_AI27_CHAT
def test_second_child_receives_previous_child_output(
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
    ).json()
    chain = sent["subagent_chain"]
    first = client.get(f"/agent-runs/{chain[0]['agent_run_id']}", headers=auth_headers).json()
    second = client.get(f"/agent-runs/{chain[1]['agent_run_id']}", headers=auth_headers).json()
    assert "previous_child_output" in second["input_payload"]
    prev = second["input_payload"]["previous_child_output"]
    assert isinstance(prev, dict)
    assert len(json.dumps(prev).encode("utf-8")) <= COMPACT_SUBAGENT_OUTPUT_MAX_BYTES
    assert first["parent_agent_run_id"] == second["parent_agent_run_id"]


@_SKIP_AI27_CHAT
def test_copywriter_and_researcher_single_chains_still_work(
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

    copy = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": REWRITE_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    assert len(copy["subagent_chain"]) == 1

    research = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": RESEARCH_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    assert research["subagent_chain"][0]["subagent"] == "researcher"


@_SKIP_AI27_CHAT
def test_analyst_route_no_subagent_chain(
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
    assert sent.json().get("subagent_chain") is None


def test_strategist_persona_no_forbidden_tools() -> None:
    for subagent in (
        MarketerSubAgentType.STRATEGIST,
        MarketerSubAgentType.RESEARCHER,
        MarketerSubAgentType.COPYWRITER,
    ):
        profile = get_subagent(subagent)
        assert profile.allowed_tools.isdisjoint(FORBIDDEN_PERSONA_TOOLS)


@_SKIP_AI27_CHAT
@pytest.mark.asyncio
async def test_child_cannot_spawn_chain(
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
        json={"content": REWRITE_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    child_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["subagent_chain"][0]["agent_run_id"]),
    )
    assert child_run is not None

    with pytest.raises(InvalidStateError, match="Only orchestrator"):
        await run_subagent_child(
            db_session,
            parent_run=child_run,
            subagent_type=MarketerSubAgentType.COPYWRITER,
            input_payload={"prompt": "nested"},
            owner_id=owner_id,
        )


@_SKIP_AI27_CHAT
@pytest.mark.asyncio
async def test_execute_subagent_rejects_second_child_on_same_parent(
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
        json={"content": REWRITE_MESSAGE, "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    parent_run = await AgentRunService(db_session).get_run(owner_id, UUID(sent["agent_run_id"]))
    assert parent_run is not None
    assert await AgentRunService(db_session).count_children(parent_run.id, owner_id) == 1

    with pytest.raises(InvalidStateError, match="already has"):
        await execute_subagent(
            db_session,
            parent_run=parent_run,
            subagent_type=MarketerSubAgentType.COPYWRITER,
            input_payload={"prompt": "second"},
            owner_id=owner_id,
        )


def test_chain_execution_module_no_langgraph() -> None:
    from app.agents.marketer import chain_execution as chain_execution_module

    source = inspect.getsource(chain_execution_module).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in source

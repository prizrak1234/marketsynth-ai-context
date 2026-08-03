"""Phase AI.16 — General → Programmer domain skeleton."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from app.agents.general.contracts import GeneralDomain
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.programmer.contracts import PROGRAMMER_FORBIDDEN_TOOL_MARKERS
from app.agents.run_depth import MAX_AGENT_RUN_DEPTH, compute_agent_run_depth
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST, get_agent_tool_allowlist
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

PROGRAMMER_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "programmer"

LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"
PROGRAMMER_SCRIPT_MESSAGE = "Напиши скрипт для webhook интеграции"
PROGRAMMER_BOT_MESSAGE = "Сделай telegram bot для уведомлений"
PROGRAMMER_API_MESSAGE = "Нужна консультация по API автоматизации"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Programmer Domain"}, headers=headers)
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


def test_detect_programmer_domain() -> None:
    assert detect_general_domain(message=PROGRAMMER_SCRIPT_MESSAGE) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message=PROGRAMMER_BOT_MESSAGE) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message=PROGRAMMER_API_MESSAGE) == GeneralDomain.PROGRAMMER


def test_telegram_bot_routes_programmer_not_marketing() -> None:
    assert detect_general_domain(message=PROGRAMMER_BOT_MESSAGE) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message="Напиши пост в telegram") == GeneralDomain.MARKETING


def test_marketing_domain_unchanged() -> None:
    assert detect_general_domain(message=LAUNCH_MESSAGE) == GeneralDomain.MARKETING


def test_unknown_domain_unchanged() -> None:
    assert detect_general_domain(message=UNKNOWN_MESSAGE) == GeneralDomain.UNKNOWN


def test_programmer_tool_profile_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.PROGRAMMER] == frozenset()
    assert get_agent_tool_allowlist(AgentType.PROGRAMMER) == frozenset()


def test_programmer_allowlist_disjoint_forbidden_markers() -> None:
    allowlist = get_agent_tool_allowlist(AgentType.PROGRAMMER)
    registered = {tool.name.lower() for tool in get_tool_registry().list_registered()}
    for name in registered:
        for marker in PROGRAMMER_FORBIDDEN_TOOL_MARKERS:
            assert marker not in name
    assert allowlist.isdisjoint(registered) or allowlist == frozenset()


def test_programmer_execution_module_no_shell_github_filesystem() -> None:
    combined = (
        (PROGRAMMER_DIR / "execution.py").read_text(encoding="utf-8")
        + (PROGRAMMER_DIR / "prompts.py").read_text(encoding="utf-8")
    ).lower()
    for marker in ("subprocess", "github", "shell.execute", "filesystem.write", "deploy."):
        assert marker not in combined


def test_unknown_intent_clarification_no_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": UNKNOWN_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("general_delegation") is None
    assert UNKNOWN_DOMAIN_CLARIFICATION in body["assistant_message"]["content"]


def test_programmer_intent_delegates_with_general_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_SCRIPT_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    delegation = body["general_delegation"]
    assert delegation is not None
    assert delegation["domain"] == "programmer"

    general_run_id = body["agent_run_id"]
    programmer_run_id = delegation["agent_run_id"]

    general_run = client.get(f"/agent-runs/{general_run_id}", headers=auth_headers).json()
    programmer_run = client.get(f"/agent-runs/{programmer_run_id}", headers=auth_headers).json()

    assert general_run["parent_agent_run_id"] is None
    assert programmer_run["parent_agent_run_id"] == general_run_id
    assert programmer_run["agent_id"] == programmer_id
    assert programmer_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert programmer_run["input_payload"]["delegated_domain"] == "programmer"
    assert body.get("subagent_chain") is None

    output = programmer_run.get("output_payload") or {}
    draft = output.get("technical_task_draft")
    assert draft is not None
    assert draft.get("persisted") is False


def test_marketing_intent_still_delegates_to_marketer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Перепиши этот пост", "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["general_delegation"]["domain"] == "marketing"


@pytest.mark.asyncio
async def test_programmer_path_depth_model(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="programmer")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_API_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    agent_runs = AgentRunService(db_session)

    general_run = await agent_runs.get_run(owner_id, UUID(sent["agent_run_id"]))
    programmer_run = await agent_runs.get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
    assert general_run is not None
    assert programmer_run is not None

    assert await compute_agent_run_depth(db_session, general_run, owner_id) == 0
    assert await compute_agent_run_depth(db_session, programmer_run, owner_id) == 1

    assert await agent_runs.count_children(programmer_run.id, owner_id) == 0


@pytest.mark.asyncio
async def test_programmer_child_cannot_spawn_subagent(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    programmer_agent_id = UUID(
        _create_agent(client, auth_headers, project_id, agent_type="programmer"),
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_SCRIPT_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    programmer_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
    assert programmer_run is not None
    depth = await compute_agent_run_depth(db_session, programmer_run, owner_id)
    assert depth == 1

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=programmer_agent_id,
            task_id=programmer_run.task_id,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=programmer_run.id,
        )

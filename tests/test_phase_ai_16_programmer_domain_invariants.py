"""Phase AI.16.1 — Programmer domain freeze invariants (guard)."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import UUID

import pytest
from app.agents.general.contracts import GeneralDomain
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.programmer import execution as programmer_execution_module
from app.agents.programmer.contracts import PROGRAMMER_FORBIDDEN_TOOL_MARKERS
from app.agents.programmer.execution import build_technical_task_draft, merge_programmer_output_payload
from app.agents.run_depth import compute_agent_run_depth
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST, get_agent_tool_allowlist
from app.tools.permissions import DEFAULT_TOOL_PERMISSION_MATRIX
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

PROGRAMMER_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "programmer"
UI_DELEGATION_PANEL = (
    Path(__file__).resolve().parents[1] / "web" / "src" / "components" / "agent-chat" / "general-delegation-panel.tsx"
)

LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"
TELEGRAM_BOT_MESSAGE = "Сделай telegram bot для уведомлений"
TELEGRAM_POST_MESSAGE = "Напиши пост в telegram"

FROZEN_PROGRAMMER_ROUTING: tuple[tuple[str, GeneralDomain], ...] = (
    (TELEGRAM_BOT_MESSAGE, GeneralDomain.PROGRAMMER),
    ("Нужна консультация по API", GeneralDomain.PROGRAMMER),
    ("Напиши скрипт автоматизации", GeneralDomain.PROGRAMMER),
    ("Сверстай блок на tilda", GeneralDomain.PROGRAMMER),
    ("Настрой webhook для CRM", GeneralDomain.PROGRAMMER),
)

FROZEN_FORBIDDEN_SOURCE_MARKERS = (
    "shell",
    "github",
    "filesystem",
    "deploy",
    "secret",
)

EXECUTION_FORBIDDEN_MARKERS = (
    "langgraph",
    "handoff",
    "parallel_execution",
    "swarm",
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.16.1 Invariants"}, headers=headers)
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


# --- Router freeze ---


@pytest.mark.parametrize(("message", "expected"), FROZEN_PROGRAMMER_ROUTING)
def test_invariant_programmer_phrases_route_to_programmer(
    message: str,
    expected: GeneralDomain,
) -> None:
    assert detect_general_domain(message=message) == expected


def test_invariant_telegram_bot_not_marketing() -> None:
    assert detect_general_domain(message=TELEGRAM_BOT_MESSAGE) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message=TELEGRAM_POST_MESSAGE) == GeneralDomain.MARKETING


def test_invariant_marketing_launch_still_marketing() -> None:
    assert detect_general_domain(message=LAUNCH_MESSAGE) == GeneralDomain.MARKETING


def test_invariant_unknown_still_clarification_domain() -> None:
    assert detect_general_domain(message=UNKNOWN_MESSAGE) == GeneralDomain.UNKNOWN


# --- Tools & safety ---


def test_invariant_programmer_tool_profile_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.PROGRAMMER] == frozenset()
    assert get_agent_tool_allowlist(AgentType.PROGRAMMER) == frozenset()


def test_invariant_programmer_in_permission_matrix() -> None:
    assert AgentType.PROGRAMMER in DEFAULT_TOOL_PERMISSION_MATRIX
    policy = DEFAULT_TOOL_PERMISSION_MATRIX[AgentType.PROGRAMMER]
    assert policy.allowed_tools == set()
    assert policy.execution_mode.value == "no_op"


def test_invariant_programmer_allowlist_has_no_registered_tools() -> None:
    allowlist = get_agent_tool_allowlist(AgentType.PROGRAMMER)
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    assert allowlist.isdisjoint(registered)


def test_invariant_programmer_contracts_lists_forbidden_tool_markers() -> None:
    for marker in FROZEN_FORBIDDEN_SOURCE_MARKERS:
        assert any(marker in entry for entry in PROGRAMMER_FORBIDDEN_TOOL_MARKERS)


def test_invariant_programmer_execution_source_no_shell_github_filesystem_deploy() -> None:
    source = (PROGRAMMER_DIR / "execution.py").read_text(encoding="utf-8").lower()
    for marker in (
        "subprocess",
        "github",
        "shell.execute",
        "filesystem.write",
        "deploy(",
        "httpx",
        "aiohttp",
    ):
        assert marker not in source


def test_invariant_programmer_execution_no_langgraph_handoff() -> None:
    source = inspect.getsource(programmer_execution_module).lower()
    for marker in EXECUTION_FORBIDDEN_MARKERS:
        assert marker not in source


def test_invariant_programmer_execution_no_repo_or_shell_imports() -> None:
    source = inspect.getsource(programmer_execution_module).lower()
    for marker in ("subprocess", "github", "httpx", "aiohttp", "open(", "pathlib.write"):
        assert marker not in source


# --- technical_task_draft contract ---


def test_invariant_technical_task_draft_persisted_false() -> None:
    draft = build_technical_task_draft(message="API design", assistant_excerpt="Mock answer")
    assert draft["persisted"] is False
    merged = merge_programmer_output_payload(
        run=type("Run", (), {"output_payload": {"content": "Mock answer"}})(),
        message="API design",
    )
    assert merged["technical_task_draft"]["persisted"] is False
    assert merged["programmer_mode"] == "consultation"


# --- UI ---


def test_invariant_ui_delegation_panel_generic_for_programmer() -> None:
    source = UI_DELEGATION_PANEL.read_text(encoding="utf-8")
    assert 'case "programmer"' in source
    assert 'case "marketing"' in source
    assert "Delegated to" in source
    assert "Specialist run" in source
    assert "Orchestrator run" not in source


# --- Integration ---


def test_invariant_unknown_chat_no_delegation(
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


def test_invariant_general_parent_and_programmer_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Настрой webhook для API", "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["general_delegation"]["domain"] == "programmer"

    general_run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    programmer_run = client.get(
        f"/agent-runs/{body['general_delegation']['agent_run_id']}",
        headers=auth_headers,
    ).json()

    assert general_run["parent_agent_run_id"] is None
    assert programmer_run["parent_agent_run_id"] == body["agent_run_id"]
    assert programmer_run["agent_id"] == programmer_id
    assert programmer_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert body.get("subagent_chain") is None

    draft = (programmer_run.get("output_payload") or {}).get("technical_task_draft")
    assert draft is not None
    assert draft["persisted"] is False


def test_invariant_marketing_delegation_unchanged(
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
    assert sent.json()["general_delegation"]["domain"] == "marketing"


@pytest.mark.asyncio
async def test_invariant_programmer_child_depth_one_no_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="programmer")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Напиши скрипт для API", "agent_id": general_id},
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
async def test_invariant_programmer_child_cannot_spawn_children(
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
        json={"content": "Нужен скрипт на python", "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    programmer_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
    assert programmer_run is not None

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=programmer_agent_id,
            task_id=programmer_run.task_id,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=programmer_run.id,
        )

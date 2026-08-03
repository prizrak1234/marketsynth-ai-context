"""Phase AI.15.1 — General Agent freeze invariants (guard)."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import UUID

import pytest
from app.agents.general.contracts import GeneralDomain
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.marketer.execution import SUBAGENT_EXECUTION_SOURCE
from app.agents.marketer.registry import FORBIDDEN_PERSONA_TOOLS
from app.agents.run_depth import MAX_AGENT_RUN_DEPTH, compute_agent_run_depth
from app.core.exceptions import InvalidStateError
from app.schemas.agent_chat import AgentChatGeneralDelegation, AgentChatSendResponse
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST, get_agent_tool_allowlist
from fastapi.testclient import TestClient

GENERAL_MODULES = tuple(
    (Path(__file__).resolve().parents[1] / "app" / "agents" / "general").glob("*.py"),
)

LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"
PROGRAMMER_MESSAGE = "Напиши код на Python для API"
MEDIA_MESSAGE = "Смонтируй видео для YouTube"

FORBIDDEN_GENERAL_TOOLS = frozenset(
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


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.15.1 Invariants"}, headers=headers)
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


# --- Contracts & depth model ---


def test_invariant_general_domain_enum_marketing_programmer_media_unknown() -> None:
    assert set(GeneralDomain) == {
        GeneralDomain.MARKETING,
        GeneralDomain.PROGRAMMER,
        GeneralDomain.MEDIA,
        GeneralDomain.UNKNOWN,
    }


def test_invariant_max_agent_run_depth_is_two() -> None:
    assert MAX_AGENT_RUN_DEPTH == 2


def test_invariant_chat_response_has_general_delegation_field() -> None:
    assert "general_delegation" in AgentChatSendResponse.model_fields
    assert "domain" in AgentChatGeneralDelegation.model_fields
    assert "agent_run_id" in AgentChatGeneralDelegation.model_fields


def test_invariant_general_tool_profile_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.GENERAL] == frozenset()
    assert get_agent_tool_allowlist(AgentType.GENERAL) == frozenset()


def test_invariant_general_allowlist_disjoint_forbidden_tools() -> None:
    allowlist = get_agent_tool_allowlist(AgentType.GENERAL)
    assert allowlist.isdisjoint(FORBIDDEN_GENERAL_TOOLS)
    assert allowlist.isdisjoint(FORBIDDEN_PERSONA_TOOLS)


def test_invariant_general_modules_no_langgraph_handoff() -> None:
    combined = "".join(path.read_text(encoding="utf-8") for path in GENERAL_MODULES).lower()
    for marker in EXECUTION_SOURCE_FORBIDDEN_MARKERS:
        assert marker not in combined


def test_invariant_programmer_message_routes_to_programmer_domain() -> None:
    assert detect_general_domain(message=PROGRAMMER_MESSAGE) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message="Напиши скрипт для API") == GeneralDomain.PROGRAMMER


def test_invariant_youtube_video_message_routes_to_media_not_programmer() -> None:
    assert detect_general_domain(message=MEDIA_MESSAGE) == GeneralDomain.MEDIA


def test_invariant_general_contracts_no_tilda_email_domains() -> None:
    source = (Path(__file__).resolve().parents[1] / "app/agents/general/contracts.py").read_text(
        encoding="utf-8",
    )
    assert "TILDA" not in source
    assert "EMAIL" not in source


# --- Integration: delegation & depth ---


def test_invariant_marketing_intent_delegates_to_marketer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": LAUNCH_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    delegation = body["general_delegation"]
    assert delegation["domain"] == "marketing"

    general_run_id = body["agent_run_id"]
    marketer_run_id = delegation["agent_run_id"]

    general_run = client.get(f"/agent-runs/{general_run_id}", headers=auth_headers).json()
    marketer_run = client.get(f"/agent-runs/{marketer_run_id}", headers=auth_headers).json()

    assert general_run["parent_agent_run_id"] is None
    assert marketer_run["parent_agent_run_id"] == general_run_id
    assert marketer_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert marketer_run["input_payload"]["delegated_domain"] == "marketing"

    assert body.get("subagent_chain") is None
    assert marketer_run["output_payload"].get("marketing_execution_plan")
    plan_blocks = [b for b in body.get("blocks", []) if b.get("type") == "marketing_plan"]
    assert plan_blocks


def test_invariant_unknown_intent_clarification_no_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": UNKNOWN_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("general_delegation") is None
    assert body.get("subagent_chain") is None
    assert UNKNOWN_DOMAIN_CLARIFICATION in body["assistant_message"]["content"]


def test_invariant_direct_orchestrator_chat_has_no_general_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Перепиши этот пост", "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("general_delegation") is None


@pytest.mark.asyncio
async def test_invariant_run_depths_under_general_path(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": LAUNCH_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    agent_runs = AgentRunService(db_session)

    general_run = await agent_runs.get_run(owner_id, UUID(sent["agent_run_id"]))
    marketer_run = await agent_runs.get_run(owner_id, UUID(sent["general_delegation"]["agent_run_id"]))
    assert general_run is not None
    assert marketer_run is not None

    assert await compute_agent_run_depth(db_session, general_run, owner_id) == 0
    assert await compute_agent_run_depth(db_session, marketer_run, owner_id) == 1
    assert await agent_runs.count_children(marketer_run.id, owner_id) == 0


@pytest.mark.asyncio
async def test_invariant_depth_greater_than_two_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    copywriter_id = UUID(
        _create_agent(client, auth_headers, project_id, agent_type="copywriter"),
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": LAUNCH_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    marketer_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
    assert marketer_run is not None
    child = await AgentRunService(db_session).create_run(
        owner_id,
        agent_id=copywriter_id,
        task_id=marketer_run.task_id,
        input_payload={"prompt": "depth-2"},
        metadata={},
        parent_agent_run_id=marketer_run.id,
    )
    assert child is not None

    with pytest.raises(InvalidStateError, match="Maximum agent run depth exceeded"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=copywriter_id,
            task_id=child.task_id,
            input_payload={"prompt": "too deep"},
            metadata={},
            parent_agent_run_id=child.id,
        )


def test_invariant_general_execution_delegates_not_executes() -> None:
    from app.agents import general as general_package

    source = inspect.getsource(general_package.execution.execute_general_agent)
    assert "execute_marketer_orchestrator_delegation" in source
    assert "AgentRunCoordinator" not in source

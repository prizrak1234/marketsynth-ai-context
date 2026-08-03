"""Phase AI.15 — General agent skeleton (routing to Marketer only)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.general.contracts import GeneralDomain
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.marketer.execution import SUBAGENT_EXECUTION_SOURCE, run_subagent_child
from app.agents.marketer.registry import FORBIDDEN_PERSONA_TOOLS
from app.agents.run_depth import MAX_AGENT_RUN_DEPTH, compute_agent_run_depth
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST
from fastapi.testclient import TestClient

GENERAL_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "general"

LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"
MARKETING_MESSAGE = "Сделай контент-план"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "General Project"}, headers=headers)
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


def test_detect_marketing_domain() -> None:
    assert detect_general_domain(message=LAUNCH_MESSAGE) == GeneralDomain.MARKETING
    assert detect_general_domain(message=MARKETING_MESSAGE) == GeneralDomain.MARKETING


def test_detect_unknown_domain() -> None:
    assert detect_general_domain(message=UNKNOWN_MESSAGE) == GeneralDomain.UNKNOWN
    assert detect_general_domain(message="") == GeneralDomain.UNKNOWN


def test_general_has_no_forbidden_tools() -> None:
    allowlist = DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.GENERAL]
    assert allowlist == frozenset()
    assert allowlist.isdisjoint(FORBIDDEN_PERSONA_TOOLS)


def test_general_execution_router_no_tool_names() -> None:
    """Routing modules must not register approve/publish/schedule tools."""
    paths = (GENERAL_DIR / "execution.py", GENERAL_DIR / "router.py", GENERAL_DIR / "contracts.py")
    combined = "".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for marker in ("content_asset.approve", "content_asset.publish", "publication_job"):
        assert marker not in combined


def test_max_agent_run_depth_constant() -> None:
    assert MAX_AGENT_RUN_DEPTH == 2


def test_unknown_intent_returns_clarification(
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
    assert UNKNOWN_DOMAIN_CLARIFICATION in body["assistant_message"]["content"]
    assert body["subagent_chain"] is None

    parent = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert parent["parent_agent_run_id"] is None


def test_marketing_intent_delegates_to_orchestrator_planning(
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
    assert delegation is not None
    assert delegation["domain"] == "marketing"
    assert body.get("subagent_chain") is None

    general_run_id = body["agent_run_id"]
    marketer_run_id = delegation["agent_run_id"]
    assert marketer_run_id != general_run_id

    general_run = client.get(f"/agent-runs/{general_run_id}", headers=auth_headers).json()
    assert general_run["parent_agent_run_id"] is None

    marketer_run = client.get(f"/agent-runs/{marketer_run_id}", headers=auth_headers).json()
    assert marketer_run["parent_agent_run_id"] == general_run_id
    assert marketer_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert marketer_run["input_payload"]["delegated_domain"] == "marketing"
    assert marketer_run["output_payload"].get("marketing_execution_plan")

    plan_blocks = [b for b in body.get("blocks", []) if b.get("type") == "marketing_plan"]
    assert plan_blocks


@pytest.mark.asyncio
async def test_depth_greater_than_two_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    copywriter_agent_id = UUID(
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
    depth = await compute_agent_run_depth(db_session, marketer_run, owner_id)
    assert depth == 1

    agent_runs = AgentRunService(db_session)
    child = await agent_runs.create_run(
        owner_id,
        agent_id=copywriter_agent_id,
        task_id=marketer_run.task_id,
        input_payload={"prompt": "depth-2"},
        metadata={},
        parent_agent_run_id=marketer_run.id,
    )
    assert child is not None
    with pytest.raises(InvalidStateError, match="Maximum agent run depth exceeded"):
        await agent_runs.create_run(
            owner_id,
            agent_id=copywriter_agent_id,
            input_payload={"prompt": "too deep"},
            metadata={},
            parent_agent_run_id=child.id,
        )


@pytest.mark.asyncio
async def test_general_orchestrator_child_planning_has_no_subagent_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """AI.27: orchestrator under General returns a plan only — no subagent child runs."""
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Перепиши этот пост", "agent_id": general_id},
        headers=auth_headers,
    ).json()
    assert sent["general_delegation"] is not None
    assert sent["general_delegation"]["domain"] == "marketing"
    assert sent.get("subagent_chain") is None
    owner_id = UUID(sent["session"]["owner_id"])
    marketer_id = UUID(sent["general_delegation"]["agent_run_id"])
    assert await AgentRunService(db_session).count_children(marketer_id, owner_id) == 0


def test_orchestrator_chat_without_general_delegation_field(
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
    body = sent.json()
    assert body.get("general_delegation") is None
    assert body.get("subagent_chain") is None
    assert any(b.get("type") == "marketing_plan" for b in body.get("blocks", []))

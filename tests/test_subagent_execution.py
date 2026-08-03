"""Phase AI.11–AI.12 — sequential orchestrator → sub-agent execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import execute_subagent, run_subagent_child
from app.agents.marketer.registry import get_subagent
from app.core.exceptions import InvalidStateError
from app.services.agent_runs import AgentRunService
from fastapi.testclient import TestClient

_SKIP_AI27_CHAT = pytest.mark.skip(
    reason="AI.27: agent-chat uses marketing planning mode, not subagent execution",
)


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Subagent Project") -> str:
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


@_SKIP_AI27_CHAT
def test_orchestrator_delegates_copywriter_child_run(
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
        json={
            "content": "Перепиши этот пост",
            "agent_id": orchestrator_id,
        },
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["subagent_chain"] is not None
    assert body["subagent_chain"][-1]["subagent"] == "copywriter"

    parent_id = body["agent_run_id"]
    child_id = body["subagent_chain"][-1]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()

    assert parent["agent_id"] == orchestrator_id
    assert child["parent_agent_run_id"] == parent_id
    assert child["agent_id"] == copywriter_id
    assert child["status"] == "succeeded"
    assert child["project_id"] == parent["project_id"] == project_id
    assert child["owner_id"] == parent["owner_id"]
    assert child["input_payload"].get("source") == "subagent_execution"
    assert child["input_payload"].get("parent_agent_run_id") == parent_id
    assert body["assistant_message"]["agent_run_id"] == child_id


@pytest.mark.asyncio
async def test_child_run_cannot_spawn_nested_subagent_async(
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
        json={"content": "Перепиши пост", "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    child_id = UUID(sent["subagent_chain"][0]["agent_run_id"])
    owner_id = UUID(sent["session"]["owner_id"])

    child_run = await AgentRunService(db_session).get_run(owner_id, child_id)
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
def test_copywriter_child_uses_copywriter_tools_only(
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
        json={"content": "Improve this post copy", "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    child_id = UUID(sent["subagent_chain"][0]["agent_run_id"])

    logs = client.get(f"/agent-runs/{child_id}/tool-executions", headers=auth_headers)
    if logs.status_code == 200 and logs.json():
        profile = get_subagent(MarketerSubAgentType.COPYWRITER)
        forbidden = {
            "content_asset.approve",
            "content_asset.publish",
            "content_asset.schedule",
            "campaign_plan_draft.create",
        }
        for entry in logs.json():
            tool_name = entry.get("tool_name") or entry.get("name")
            if tool_name:
                assert tool_name in profile.allowed_tools or tool_name not in forbidden


def test_analyst_routing_does_not_spawn_subagent_execution(
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
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert run["status"] == "succeeded"
    assert run["parent_agent_run_id"] is None


@_SKIP_AI27_CHAT
def test_orchestrator_delegates_researcher_child_run(
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
        json={
            "content": "Исследуй аудиторию",
            "agent_id": orchestrator_id,
        },
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body["subagent_chain"] is not None
    assert body["subagent_chain"][0]["subagent"] == "researcher"

    parent_id = body["agent_run_id"]
    child_id = body["subagent_chain"][0]["agent_run_id"]

    parent = client.get(f"/agent-runs/{parent_id}", headers=auth_headers).json()
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()

    assert parent["agent_id"] == orchestrator_id
    assert child["parent_agent_run_id"] == parent_id
    assert child["agent_id"] == researcher_id
    assert child["status"] == "succeeded"
    assert child["input_payload"].get("source") == "subagent_execution"


@_SKIP_AI27_CHAT
def test_researcher_child_uses_researcher_tools_only(
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
        json={"content": "Research the audience", "agent_id": orchestrator_id},
        headers=auth_headers,
    ).json()
    child_id = UUID(sent["subagent_chain"][0]["agent_run_id"])

    logs = client.get(f"/agent-runs/{child_id}/tool-executions", headers=auth_headers)
    if logs.status_code == 200 and logs.json():
        profile = get_subagent(MarketerSubAgentType.RESEARCHER)
        forbidden = {
            "content_asset.approve",
            "content_asset.publish",
            "content_asset.schedule",
            "campaign_plan_draft.create",
        }
        for entry in logs.json():
            tool_name = entry.get("tool_name") or entry.get("name")
            if tool_name:
                assert tool_name in profile.allowed_tools or tool_name not in forbidden


def test_direct_copywriter_chat_skips_subagent_execution(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    copywriter_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="copywriter",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "content": "Перепиши пост",
            "agent_id": copywriter_id,
        },
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("subagent_execution") is None


def test_direct_researcher_chat_skips_subagent_execution(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
    )

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "content": "Исследуй аудиторию",
            "agent_id": researcher_id,
        },
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert sent.json().get("subagent_execution") is None

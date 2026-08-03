"""Agent chat workflow context tests (Phase AI.2)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.schemas.contracts import AgentType
from app.tools.write_tool_settings import is_real_write_executable
from fastapi.testclient import TestClient


def _create_project(
    client: TestClient, headers: dict[str, str], name: str = "Workflow Chat"
) -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_strategist(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Chat workflow campaign"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_campaign_id_validated_by_project_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    other_project = _create_project(client, other_auth_headers, name="Other")
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, other_auth_headers, other_project)

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Scoped?", "campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_workflow_context_in_agent_run_input_payload(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "What should I do next?", "campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    run_id = sent.json()["agent_run_id"]

    run = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    agent_chat = run["input_payload"]["agent_chat"]
    assert agent_chat["campaign_id"] == campaign_id
    assert agent_chat["workflow_state"] == "planning"
    assert agent_chat["next_recommended_action"] == "create_plan_draft"
    assert agent_chat["pending_review_assets"] == 0


def test_prompt_includes_workflow_context() -> None:
    campaign_id = uuid4()
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.STRATEGIST,
            input_payload={
                "prompt": "Next step?",
                "agent_chat": {
                    "campaign_id": str(campaign_id),
                    "workflow_state": "ready_for_review",
                    "next_recommended_action": "review_assets",
                    "pending_review_assets": 2,
                },
            },
        ),
    )
    combined = "\n".join(message.content for message in built.messages)
    assert "Campaign workflow context" in combined
    assert "ready_for_review" in combined
    assert "Review Queue" in combined
    assert "review_assets" in combined
    assert "Never claim" in combined or "never claim" in combined.lower()


def test_without_campaign_id_preserves_legacy_flow(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Legacy content field still works"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    sent_body = sent.json()
    run = client.get(f"/agent-runs/{sent_body['agent_run_id']}", headers=auth_headers).json()
    assert "agent_chat" not in run["input_payload"]


def test_write_tools_still_disabled_with_campaign_context(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Do not write", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    logs = client.get(
        f"/agent-runs/{sent['agent_run_id']}/tool-executions",
        headers=auth_headers,
    ).json()
    for entry in logs:
        assert not is_real_write_executable(entry["tool_name"])

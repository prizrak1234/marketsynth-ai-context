"""Agent chat campaign_plan_draft.create tests (Phase AI.3)."""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.db.repositories.campaign_plan_drafts import CampaignPlanDraftRepository
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.schemas.contracts import AgentType
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    agent_chat_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.marketing_tools import CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import is_real_write_executable
from fastapi.testclient import TestClient


def _sample_plan_payload() -> dict:
    return {
        "goal": "Telegram product launch",
        "target_audience": "SMB owners",
        "key_message": "Launch in Telegram",
        "content_items": [
            {
                "title": "Launch post",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": "Short teaser",
            },
        ],
    }


@pytest.fixture
def enable_agent_chat_plan_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def chat_tools_only_master_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Plan Draft"}, headers=headers)
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


def _create_copywriter(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Telegram launch"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _mock_plan_draft_tool_call(project_id: str, campaign_id: str) -> dict:
    return {
        "id": "call_chat_plan",
        "type": "function",
        "function": {
            "name": CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            "arguments": {
                "project_id": project_id,
                "campaign_id": campaign_id,
                "title": "Telegram launch plan",
                "plan_payload": _sample_plan_payload(),
            },
        },
    }


def test_agent_chat_tools_flag_off_disables_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "false")
    get_settings.cache_clear()
    assert agent_chat_tools_enabled() is False
    tools = list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    assert tools == []


def test_write_flags_off_disables_chat_tools(chat_tools_only_master_flag: None) -> None:
    assert agent_chat_tools_enabled() is False
    assert is_real_write_executable(CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME) is False


def test_allowlisted_tools_when_flags_on(enable_agent_chat_plan_tools: None) -> None:
    assert agent_chat_tools_enabled() is True
    names = {
        tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    }
    assert names == set(AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES)
    copywriter_tools = list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER)
    assert copywriter_tools == []


def test_build_run_input_includes_plan_draft_hint(
    enable_agent_chat_plan_tools: None,
) -> None:
    from uuid import uuid4

    project_id = uuid4()
    campaign_id = uuid4()
    payload = build_agent_chat_run_input_payload(
        prompt="Create a plan",
        project_id=project_id,
        workflow_context={
            "campaign_id": str(campaign_id),
            "workflow_state": "planning",
            "next_recommended_action": "create_plan_draft",
            "pending_review_assets": 0,
        },
    )
    assert payload["project_id"] == str(project_id)
    assert payload["agent_chat"]["plan_draft_create_enabled"] is True


def test_prompt_includes_plan_draft_rules_when_tools_on(
    enable_agent_chat_plan_tools: None,
) -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=__import__("uuid").uuid4(),
            agent_type=AgentType.STRATEGIST,
            input_payload={
                "prompt": "Создай план кампании",
                "agent_chat": {
                    "campaign_id": str(__import__("uuid").uuid4()),
                    "workflow_state": "planning",
                    "next_recommended_action": "create_plan_draft",
                    "pending_review_assets": 0,
                },
            },
        ),
    )
    combined = "\n".join(message.content for message in built.messages)
    assert "campaign_plan_draft.create" in combined
    assert "Generate Assets" in combined


def test_success_creates_plan_draft_via_chat(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_plan_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    original_build = build_agent_chat_run_input_payload

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = original_build(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_plan_draft_tool_call(
            str(project_id),
            campaign_id,
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "message": "Создай план кампании для запуска продукта в Telegram",
            "campaign_id": campaign_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plan_draft"] is not None
    assert body["plan_draft"]["draft_id"]
    assert body["plan_draft"]["campaign_id"] == campaign_id
    assert "draft_id:" in body["assistant_message"]["content"]
    assert "Generate Assets" in body["assistant_message"]["content"]

    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME in json.dumps(run["input_payload"])
    assert "agent_chat" in run["input_payload"]

    drafts = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        headers=auth_headers,
    )
    assert drafts.status_code == 200
    assert any(item["id"] == body["plan_draft"]["draft_id"] for item in drafts.json())


@pytest.mark.asyncio
async def test_source_agent_run_id_set(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_plan_tools: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_plan_draft_tool_call(str(project_id), campaign_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Plan please", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    row = await CampaignPlanDraftRepository(db_session).get_by_id_for_campaign(
        UUID(body["plan_draft"]["draft_id"]),
        UUID(body["session"]["owner_id"]),
        UUID(project_id),
        UUID(campaign_id),
    )
    assert row is not None
    assert str(row.source_agent_run_id) == body["agent_run_id"]


def test_no_assets_or_jobs_created(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_plan_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_plan_draft_tool_call(str(project_id), campaign_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Plan", "campaign_id": campaign_id},
        headers=auth_headers,
    )

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers)
    assert assets.status_code == 200
    campaign_assets = [item for item in assets.json() if item.get("campaign_id") == campaign_id]
    assert campaign_assets == []

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        campaign_jobs = [item for item in items if item.get("campaign_id") == campaign_id]
        assert campaign_jobs == []


def test_forbidden_agent_type_gets_no_chat_tools(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_plan_tools: None,
) -> None:
    project_id = _create_project(client, auth_headers)
    copywriter_id = _create_copywriter(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "message": "Create plan",
            "campaign_id": campaign_id,
            "agent_id": copywriter_id,
        },
        headers=auth_headers,
    )
    assert sent.status_code == 200
    run_id = sent.json()["agent_run_id"]
    logs = client.get(f"/agent-runs/{run_id}/tool-executions", headers=auth_headers).json()
    assert logs == []
    assert sent.json()["plan_draft"] is None


def test_audit_log_records_plan_draft_tool(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_plan_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    campaign_id = _create_campaign(client, auth_headers, project_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_plan_draft_tool_call(str(project_id), campaign_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Plan", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    logs = client.get(
        f"/agent-runs/{body['agent_run_id']}/tool-executions",
        headers=auth_headers,
    ).json()
    assert len(logs) == 1
    assert logs[0]["tool_name"] == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
    assert logs[0]["status"] == "succeeded"


def test_response_compact_without_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Hello"},
        headers=auth_headers,
    ).json()
    assert body["plan_draft"] is None

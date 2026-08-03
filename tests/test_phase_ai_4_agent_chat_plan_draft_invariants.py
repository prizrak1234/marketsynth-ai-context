"""Phase AI.4 — agent chat plan-draft readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.db.repositories.campaign_plan_drafts import CampaignPlanDraftRepository
from app.executors import agent_run_executor as agent_run_executor_module
from app.schemas.contracts import AgentType
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    agent_chat_generate_assets_tools_enabled,
    agent_chat_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    format_campaign_plan_draft_create_result,
)
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import (
    CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES,
    campaign_plan_draft_generate_assets_enabled,
    is_write_tool_visible_to_agent,
)
from fastapi.testclient import TestClient

CHAT_ALLOWED_AGENT_TYPES = frozenset(CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES)
CHAT_DENIED_AGENT_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.ANALYST,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
    },
)

AI_4_CHAT_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
        "content_asset.create_draft",
        "content_asset.create_revision",
    },
)

PLAN_DRAFT_COMPACT_RESULT_KEYS = frozenset(
    {"draft_id", "campaign_id", "status", "created_at"},
)


def _sample_plan_payload() -> dict:
    return {
        "goal": "Telegram launch",
        "target_audience": "SMB",
        "key_message": "Launch",
        "content_items": [
            {
                "title": "Post",
                "channel": "telegram",
                "format": "text",
            },
        ],
    }


@pytest.fixture
def all_chat_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def chat_flag_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_invariant_chat_tools_disabled_by_default() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.agent_chat_tools_enabled is False
    assert agent_chat_tools_enabled() is False
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST) == []


def test_invariant_chat_tools_require_all_write_flags(chat_flag_only: None) -> None:
    assert agent_chat_tools_enabled() is False


@pytest.mark.parametrize(
    "missing",
    [
        "AGENT_CHAT_TOOLS_ENABLED",
        "AGENT_WRITE_TOOLS_ENABLED",
        "CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED",
    ],
)
def test_invariant_chat_tools_off_if_any_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.delenv(missing, raising=False)
    get_settings.cache_clear()
    assert agent_chat_tools_enabled() is False


def test_invariant_chat_tools_on_only_when_all_flags(all_chat_flags_on: None) -> None:
    assert agent_chat_tools_enabled() is True


def test_invariant_chat_tool_profile_exact_allowlist(all_chat_flags_on: None) -> None:
    for agent_type in CHAT_ALLOWED_AGENT_TYPES:
        names = {tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), agent_type)}
        assert names == set(AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES)
    assert frozenset(
        {
            CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            "marketing_campaign.get",
            "marketing_campaign.workflow",
        },
    ) == AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES
    assert "campaign_plan_draft.generate_assets" in AGENT_CHAT_TOOL_NAMES


def test_invariant_generate_assets_gated_and_chat_only(all_chat_flags_on: None) -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    assert "campaign_plan_draft.generate_assets" in registered
    assert campaign_plan_draft_generate_assets_enabled() is False
    assert agent_chat_generate_assets_tools_enabled() is False
    assert "campaign_plan_draft.generate_assets" not in {
        tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    }
    for forbidden in AI_4_CHAT_FORBIDDEN_TOOL_NAMES:
        assert forbidden not in AGENT_CHAT_TOOL_NAMES
    for name in ("content_asset.approve", "content_asset.publish"):
        assert name in FORBIDDEN_AGENT_TOOL_NAMES
    for name in ("content_asset.schedule", "publication_job.schedule", "publication_job.create"):
        assert name not in registered


def test_invariant_generate_assets_not_registered_as_agent_tool() -> None:
    pytest.skip("Replaced by test_invariant_generate_assets_gated_and_chat_only (Phase AI.5)")


@pytest.mark.parametrize("agent_type", sorted(CHAT_DENIED_AGENT_TYPES, key=lambda t: t.value))
def test_invariant_forbidden_agent_types_get_no_chat_tools(
    all_chat_flags_on: None,
    agent_type: AgentType,
) -> None:
    assert list_tools_for_agent_chat(get_tool_registry(), agent_type) == []
    assert is_write_tool_visible_to_agent(agent_type, CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME) is (
        agent_type in CHAT_ALLOWED_AGENT_TYPES
    )


def test_invariant_content_asset_create_draft_not_in_chat_profile(
    all_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    names = {
        tool.name
        for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    }
    assert "content_asset.create_draft" not in names


def test_invariant_executor_uses_chat_tool_resolver_for_agent_chat_runs() -> None:
    source = inspect.getsource(agent_run_executor_module.AgentRunExecutor.execute_run)
    assert "list_tools_for_agent_chat" in source
    assert 'run_metadata.get("agent_chat")' in source


def test_invariant_plan_draft_tool_result_is_compact() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        campaign_id=uuid4(),
        status=SimpleNamespace(value="draft"),
        created_at=datetime.now(UTC),
    )
    payload = format_campaign_plan_draft_create_result(row)
    assert set(payload.keys()) == PLAN_DRAFT_COMPACT_RESULT_KEYS
    assert "plan_payload" not in payload
    assert "content_items" not in json.dumps(payload)


def _mock_plan_draft_tool_call(project_id: str, campaign_id: str) -> dict:
    return {
        "id": "call_ai4_plan",
        "type": "function",
        "function": {
            "name": CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            "arguments": {
                "project_id": project_id,
                "campaign_id": campaign_id,
                "title": "AI.4 freeze plan",
                "plan_payload": _sample_plan_payload(),
            },
        },
    }


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI4 Chat"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_strategist(client: TestClient, headers: dict[str, str], project_id: str) -> None:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=headers,
    )
    assert response.status_code == 201


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "AI4 campaign"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_invariant_chat_draft_does_not_create_assets_or_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
    all_chat_flags_on: None,
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
        json={"message": "Создай план", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers)
    assert assets.status_code == 200
    assert [a for a in assets.json() if a.get("campaign_id") == campaign_id] == []

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        assert [i for i in items if i.get("campaign_id") == campaign_id] == []

    assert body["plan_draft"] is not None
    assert set(body["plan_draft"].keys()) <= {"draft_id", "campaign_id", "title"}
    assert "plan_payload" not in json.dumps(body["plan_draft"])
    assistant = body["assistant_message"]["content"]
    assert "content_items" not in assistant
    assert "target_audience" not in assistant
    assert "draft_id:" in assistant
    assert "Generate Assets" in assistant


def test_invariant_audit_log_records_plan_draft_tool(
    client: TestClient,
    auth_headers: dict[str, str],
    all_chat_flags_on: None,
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
    assert logs[0]["execution_mode"] == "write"


@pytest.mark.asyncio
async def test_invariant_source_agent_run_id_on_chat_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    all_chat_flags_on: None,
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
        json={"message": "Plan", "campaign_id": campaign_id},
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

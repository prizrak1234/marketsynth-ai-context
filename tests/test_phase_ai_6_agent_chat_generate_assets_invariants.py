"""Phase AI.6 — agent chat generate-assets bulk-write readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.executors import agent_run_executor as agent_run_executor_module
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import AgentType
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    agent_chat_generate_assets_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    format_campaign_plan_draft_generate_assets_result,
)
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import (
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES,
    campaign_plan_draft_generate_assets_enabled,
    is_real_write_executable,
)
from fastapi.testclient import TestClient

GENERATE_ASSETS_ALLOWED = frozenset(CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES)

GENERATE_ASSETS_COMPACT_KEYS = frozenset(
    {"created_count", "already_generated", "asset_ids"},
)

AI_6_CHAT_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
        "content_asset.create_draft",
    },
)

PLAN_PAYLOAD_LEAK_MARKERS = (
    "plan_payload",
    "content_items",
    "target_audience",
    "key_message",
    '"goal"',
    '"notes"',
)

GENERATE_REQUIRED_FLAGS = (
    "AGENT_WRITE_TOOLS_ENABLED",
    "CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED",
    "AGENT_CHAT_TOOLS_ENABLED",
    "TOOLS_PROVIDER_ENABLED",
)


def _sample_plan_payload(*, item_count: int = 3) -> dict:
    return {
        "goal": "Telegram launch",
        "target_audience": "SMB",
        "key_message": "Launch",
        "content_items": [
            {
                "title": f"Post {index}",
                "channel": "telegram",
                "format": "text",
            }
            for index in range(item_count)
        ],
    }


@pytest.fixture
def all_generate_chat_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in GENERATE_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def generate_flag_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "false")
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_invariant_generate_assets_hidden_by_default() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.agent_write_tool_campaign_plan_draft_generate_assets_enabled is False
    assert campaign_plan_draft_generate_assets_enabled() is False
    assert agent_chat_generate_assets_tools_enabled() is False
    assert is_real_write_executable(CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME) is False
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.ORCHESTRATOR) == []


def test_invariant_generate_requires_all_flags(generate_flag_only: None) -> None:
    assert agent_chat_generate_assets_tools_enabled() is False


@pytest.mark.parametrize("missing", GENERATE_REQUIRED_FLAGS)
def test_invariant_generate_off_if_any_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    for flag in GENERATE_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    monkeypatch.delenv(missing, raising=False)
    get_settings.cache_clear()
    assert agent_chat_generate_assets_tools_enabled() is False


def test_invariant_generate_on_only_when_all_flags(all_generate_chat_flags_on: None) -> None:
    assert agent_chat_generate_assets_tools_enabled() is True
    assert is_real_write_executable(CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME) is True


@pytest.mark.parametrize("agent_type", sorted(GENERATE_ASSETS_ALLOWED, key=lambda t: t.value))
def test_invariant_generate_profile_allowed_agent_types(
    all_generate_chat_flags_on: None,
    agent_type: AgentType,
) -> None:
    names = {tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), agent_type)}
    assert names == set(AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES)


def test_invariant_strategist_does_not_see_generate_assets(
    all_generate_chat_flags_on: None,
) -> None:
    names = {
        tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    }
    assert CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME not in names
    assert names == set()


def test_invariant_chat_profile_excludes_approve_schedule_publish(
    all_generate_chat_flags_on: None,
) -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in AI_6_CHAT_FORBIDDEN_TOOL_NAMES:
        assert forbidden not in AGENT_CHAT_TOOL_NAMES
        assert forbidden not in {
            tool.name
            for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.ORCHESTRATOR)
        }
    for name in ("content_asset.approve", "content_asset.publish"):
        assert name in FORBIDDEN_AGENT_TOOL_NAMES
    for name in ("content_asset.schedule", "publication_job.schedule", "publication_job.create"):
        assert name not in registered


def test_invariant_generate_assets_tool_result_is_compact() -> None:
    row = SimpleNamespace(
        created_count=3,
        already_generated=False,
        asset_ids=[uuid4(), uuid4(), uuid4()],
    )
    payload = format_campaign_plan_draft_generate_assets_result(row)
    assert set(payload.keys()) == GENERATE_ASSETS_COMPACT_KEYS
    encoded = json.dumps(payload)
    for marker in PLAN_PAYLOAD_LEAK_MARKERS:
        assert marker not in encoded


def test_invariant_executor_uses_chat_tool_resolver() -> None:
    source = inspect.getsource(agent_run_executor_module.AgentRunExecutor.execute_run)
    assert "list_tools_for_agent_chat" in source
    assert 'run_metadata.get("agent_chat")' in source


def _mock_generate_tool_call(campaign_id: str, draft_id: str) -> dict:
    return {
        "id": "call_ai6_generate",
        "type": "function",
        "function": {
            "name": CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
            "arguments": {
                "campaign_id": campaign_id,
                "draft_id": draft_id,
            },
        },
    }


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI6 Chat"}, headers=headers)
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


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "AI6 campaign"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_plan_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    item_count: int = 3,
) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={
            "title": "AI6 plan",
            "plan_payload": _sample_plan_payload(item_count=item_count),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_invariant_chat_generate_creates_only_draft_assets_no_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
    all_generate_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_generate_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Разложи план в черновики", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    assert body["generated_assets"] is not None
    assert set(body["generated_assets"].keys()) <= {
        "campaign_id",
        "draft_id",
        "created_count",
        "already_generated",
        "asset_ids",
    }
    encoded = json.dumps(body["generated_assets"])
    for marker in PLAN_PAYLOAD_LEAK_MARKERS:
        assert marker not in encoded

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers).json()
    campaign_assets = [item for item in assets if item.get("campaign_id") == campaign_id]
    assert len(campaign_assets) == 3
    assert all(item["status"] == ContentAssetStatus.DRAFT.value for item in campaign_assets)
    assert all(item.get("approved_at") is None for item in campaign_assets)

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        assert [i for i in items if i.get("campaign_id") == campaign_id] == []


def test_invariant_chat_generate_idempotent_second_call(
    client: TestClient,
    auth_headers: dict[str, str],
    all_generate_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="content_planner")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_generate_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    first = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    assert first["generated_assets"]["created_count"] == 3
    first_ids = set(first["generated_assets"]["asset_ids"])

    second = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate again", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    assert second["generated_assets"]["already_generated"] is True
    assert second["generated_assets"]["created_count"] == 0
    assert set(second["generated_assets"]["asset_ids"]) == first_ids

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers).json()
    assert len([a for a in assets if a.get("campaign_id") == campaign_id]) == 3


@pytest.mark.asyncio
async def test_invariant_partial_state_returns_error_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
    all_generate_chat_flags_on: None,
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=3)

    seeded = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": "Partial seed",
            "body": "seed",
            "campaign_id": campaign_id,
            "metadata": {
                "source_plan_draft_id": draft_id,
                "plan_item_index": 0,
            },
        },
        headers=auth_headers,
    )
    assert seeded.status_code == 201, seeded.text

    owner_id = UUID(
        client.get(f"/projects/{project_id}", headers=auth_headers).json()["owner_id"],
    )
    result = await SafeNoOpToolExecutor(get_tool_registry(), session=db_session).execute(
        ToolCall(
            id="call_ai6_partial",
            name=CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
            arguments={"campaign_id": campaign_id, "draft_id": draft_id},
        ),
        ToolExecutionContext(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=UUID(agent_id),
            agent_type=AgentType.ORCHESTRATOR,
            agent_run_id=uuid4(),
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == "invalid_arguments"
    assert result.metadata["reason"] == "plan_draft_generation_partial_state"


def test_invariant_audit_log_records_generate_assets_tool(
    client: TestClient,
    auth_headers: dict[str, str],
    all_generate_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_generate_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    logs = client.get(
        f"/agent-runs/{body['agent_run_id']}/tool-executions",
        headers=auth_headers,
    ).json()
    generate_logs = [
        log for log in logs if log["tool_name"] == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME
    ]
    assert len(generate_logs) == 1
    assert generate_logs[0]["status"] == "succeeded"
    assert generate_logs[0]["execution_mode"] == "write"
    preview = generate_logs[0].get("result_preview") or {}
    assert preview.get("created_count") == 3
    assert preview.get("ok") is True
    assert "plan_payload" not in json.dumps(preview)

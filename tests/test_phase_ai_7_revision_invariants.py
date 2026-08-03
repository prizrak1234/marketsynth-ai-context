"""Phase AI.7.1 — agent chat content revision readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.executors import agent_run_executor as agent_run_executor_module
from app.marketing.contracts import ContentAssetStatus
from app.schemas.agent_chat import AgentChatRevisedAsset
from app.schemas.contracts import AgentType
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES,
    AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    agent_chat_revision_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    format_content_asset_create_revision_result,
)
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import (
    content_asset_create_revision_enabled,
    is_real_write_executable,
)
from fastapi.testclient import TestClient

REVISION_ALLOWED = frozenset(AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES)

REVISION_DENIED_AGENT_TYPES = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
        AgentType.ANALYST,
    },
)

REVISION_COMPACT_TOOL_KEYS = frozenset(
    {
        "asset_id",
        "status",
        "current_version_number",
        "approved_version_number",
    },
)

REVISED_ASSET_RESPONSE_KEYS = frozenset({"asset_id", "version"})

AI_7_CHAT_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)

REVISION_REQUIRED_FLAGS = (
    "AGENT_WRITE_TOOLS_ENABLED",
    "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
    "AGENT_CHAT_TOOLS_ENABLED",
    "TOOLS_PROVIDER_ENABLED",
)

BODY_LEAK_MARKERS = (
    '"body"',
    "body_preview",
    "Продающий текст",
    "revision draft body",
)


@pytest.fixture
def all_revision_chat_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in REVISION_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def revision_flag_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "false")
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_invariant_revision_hidden_by_default() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.agent_write_tool_content_asset_revision_enabled is False
    assert content_asset_create_revision_enabled() is False
    assert agent_chat_revision_tools_enabled() is False
    assert is_real_write_executable(CONTENT_ASSET_CREATE_REVISION_TOOL_NAME) is False
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER) == []


def test_invariant_revision_requires_all_flags(revision_flag_only: None) -> None:
    assert agent_chat_revision_tools_enabled() is False


@pytest.mark.parametrize("missing", REVISION_REQUIRED_FLAGS)
def test_invariant_revision_off_if_any_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    for flag in REVISION_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    monkeypatch.delenv(missing, raising=False)
    get_settings.cache_clear()
    assert agent_chat_revision_tools_enabled() is False


def test_invariant_revision_on_only_when_all_flags(all_revision_chat_flags_on: None) -> None:
    assert agent_chat_revision_tools_enabled() is True
    assert is_real_write_executable(CONTENT_ASSET_CREATE_REVISION_TOOL_NAME) is True


@pytest.mark.parametrize("agent_type", sorted(REVISION_ALLOWED, key=lambda t: t.value))
def test_invariant_revision_profile_allowed_agent_types(
    all_revision_chat_flags_on: None,
    agent_type: AgentType,
) -> None:
    names = {tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), agent_type)}
    assert names == set(AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES)


@pytest.mark.parametrize("agent_type", sorted(REVISION_DENIED_AGENT_TYPES, key=lambda t: t.value))
def test_invariant_revision_denied_agent_types_empty_profile(
    all_revision_chat_flags_on: None,
    agent_type: AgentType,
) -> None:
    assert list_tools_for_agent_chat(get_tool_registry(), agent_type) == []


def test_invariant_chat_profile_excludes_approve_schedule_publish_jobs(
    all_revision_chat_flags_on: None,
) -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in AI_7_CHAT_FORBIDDEN_TOOL_NAMES:
        assert forbidden not in AGENT_CHAT_TOOL_NAMES
        assert forbidden not in {
            tool.name
            for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER)
        }
    for name in ("content_asset.approve", "content_asset.publish"):
        assert name in FORBIDDEN_AGENT_TOOL_NAMES
    for name in ("content_asset.schedule", "publication_job.schedule", "publication_job.create"):
        assert name not in registered


def test_invariant_revision_tool_result_is_compact_no_body() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        status=type("S", (), {"value": ContentAssetStatus.DRAFT.value})(),
        current_version_number=4,
        approved_version_number=None,
    )
    payload = format_content_asset_create_revision_result(row)
    assert set(payload.keys()) == REVISION_COMPACT_TOOL_KEYS
    assert "body" not in payload
    encoded = json.dumps(payload)
    for marker in BODY_LEAK_MARKERS:
        assert marker not in encoded


def test_invariant_revised_asset_schema_keys_only() -> None:
    fields = set(AgentChatRevisedAsset.model_fields.keys())
    assert fields == REVISED_ASSET_RESPONSE_KEYS


def test_invariant_executor_uses_chat_tool_resolver() -> None:
    source = inspect.getsource(agent_run_executor_module.AgentRunExecutor.execute_run)
    assert "list_tools_for_agent_chat" in source
    assert 'run_metadata.get("agent_chat")' in source


def _mock_revision_tool_call(project_id: str, asset_id: str, body: str) -> dict:
    return {
        "id": "call_ai71_revision",
        "type": "function",
        "function": {
            "name": CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            "arguments": {
                "project_id": project_id,
                "asset_id": asset_id,
                "body": body,
            },
        },
    }


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI7.1 Chat"}, headers=headers)
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
        json={"title": "AI7.1 campaign"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_draft_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    campaign_id: str,
    body: str = "Original draft body.",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": "Post",
            "body": body,
            "campaign_id": campaign_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> dict:
    response =     client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_invariant_chat_revision_draft_updates_same_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    all_revision_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    asset_id = _create_draft_asset(client, auth_headers, project_id, campaign_id=campaign_id)
    revised_body = "Invariant draft revision body."

    def _build_with_mock(*, prompt, project_id, workflow_context, revision_context=None, **_kwargs):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_revision_tool_call(
            str(project_id),
            asset_id,
            revised_body,
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Перепиши пост", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    assert body["revised_assets"] is not None
    assert len(body["revised_assets"]) == 1
    item = body["revised_assets"][0]
    assert set(item.keys()) == REVISED_ASSET_RESPONSE_KEYS
    assert item["asset_id"] == asset_id
    assert item["version"] >= 1
    encoded = json.dumps(body["revised_assets"])
    for marker in BODY_LEAK_MARKERS:
        assert marker not in encoded

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["status"] == ContentAssetStatus.DRAFT.value
    assert asset["body"] == revised_body
    assert asset.get("approved_at") is None


def test_invariant_chat_revision_approved_creates_new_draft_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    all_revision_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    source_id = _create_draft_asset(
        client,
        auth_headers,
        project_id,
        campaign_id=campaign_id,
        body="Approved source body.",
    )
    _approve_asset(client, auth_headers, project_id, source_id)
    revision_body = "Invariant approved-branch revision."

    def _build_with_mock(*, prompt, project_id, workflow_context, revision_context=None, **_kwargs):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_revision_tool_call(
            str(project_id),
            source_id,
            revision_body,
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Сделай новую редакцию", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    revised_id = body["revised_assets"][0]["asset_id"]
    assert revised_id != source_id

    source_after = client.get(
        f"/projects/{project_id}/content-assets/{source_id}",
        headers=auth_headers,
    ).json()
    assert source_after["status"] == ContentAssetStatus.APPROVED.value
    assert source_after["approved_version_number"] == 1

    revision_asset = client.get(
        f"/projects/{project_id}/content-assets/{revised_id}",
        headers=auth_headers,
    ).json()
    assert revision_asset["status"] == ContentAssetStatus.DRAFT.value
    assert revision_asset["body"] == revision_body
    assert revision_asset.get("source_asset_id") == source_id


def test_invariant_chat_revision_no_publication_jobs_or_approval(
    client: TestClient,
    auth_headers: dict[str, str],
    all_revision_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    asset_id = _create_draft_asset(client, auth_headers, project_id, campaign_id=campaign_id)

    def _build_with_mock(*, prompt, project_id, workflow_context, revision_context=None, **_kwargs):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_revision_tool_call(
            str(project_id),
            asset_id,
            "Safety check revision.",
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Improve", "campaign_id": campaign_id},
        headers=auth_headers,
    )

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["status"] == ContentAssetStatus.DRAFT.value
    assert asset.get("approved_at") is None

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        assert [i for i in items if i.get("campaign_id") == campaign_id] == []


def test_invariant_audit_log_records_revision_tool_compact_preview(
    client: TestClient,
    auth_headers: dict[str, str],
    all_revision_chat_flags_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    asset_id = _create_draft_asset(client, auth_headers, project_id, campaign_id=campaign_id)

    def _build_with_mock(*, prompt, project_id, workflow_context, revision_context=None, **_kwargs):
        payload = build_agent_chat_run_input_payload(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_revision_tool_call(
            str(project_id),
            asset_id,
            "Audit invariant body.",
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Improve", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    logs = client.get(
        f"/agent-runs/{body['agent_run_id']}/tool-executions",
        headers=auth_headers,
    ).json()
    revision_logs = [
        log for log in logs if log["tool_name"] == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
    ]
    assert len(revision_logs) == 1
    assert revision_logs[0]["status"] == "succeeded"
    assert revision_logs[0]["execution_mode"] == "write"
    preview = revision_logs[0].get("result_preview") or {}
    assert preview.get("asset_id") == asset_id
    assert isinstance(preview.get("current_version_number"), int)
    assert "body" not in preview
    assert "Audit invariant body." not in json.dumps(preview)

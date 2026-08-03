"""Agent chat content_asset.create_revision tests (Phase AI.7)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.core.config import get_settings
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import AgentType
from app.services.agent_chat_revision import AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES,
    AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES,
    agent_chat_revision_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import is_real_write_executable
from fastapi.testclient import TestClient

REVISION_REQUIRED_FLAGS = (
    "AGENT_WRITE_TOOLS_ENABLED",
    "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
    "AGENT_CHAT_TOOLS_ENABLED",
    "TOOLS_PROVIDER_ENABLED",
)


@pytest.fixture
def enable_agent_chat_revision_tools(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Revision"}, headers=headers)
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
        json={"title": "Telegram launch"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_draft_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    campaign_id: str | None = None,
    title: str = "Launch post",
    body: str = "Original teaser text.",
) -> str:
    payload: dict = {
        "type": "telegram_post",
        "title": title,
        "body": body,
    }
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _mock_revision_tool_call(project_id: str, asset_id: str, body: str) -> dict:
    return {
        "id": "call_chat_revision",
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


def test_revision_tools_hidden_by_default() -> None:
    get_settings.cache_clear()
    assert agent_chat_revision_tools_enabled() is False
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER) == []


def test_revision_requires_all_flags(revision_flag_only: None) -> None:
    assert agent_chat_revision_tools_enabled() is False


@pytest.mark.parametrize("missing", REVISION_REQUIRED_FLAGS)
def test_revision_off_if_any_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    for flag in REVISION_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    monkeypatch.delenv(missing, raising=False)
    get_settings.cache_clear()
    assert agent_chat_revision_tools_enabled() is False


def test_revision_on_when_all_flags(enable_agent_chat_revision_tools: None) -> None:
    assert agent_chat_revision_tools_enabled() is True
    assert is_real_write_executable(CONTENT_ASSET_CREATE_REVISION_TOOL_NAME) is True


@pytest.mark.parametrize(
    "agent_type",
    sorted(AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES, key=lambda t: t.value),
)
def test_allowed_agent_types_see_revision_profile(
    enable_agent_chat_revision_tools: None,
    agent_type: AgentType,
) -> None:
    names = {tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), agent_type)}
    assert names == set(AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES)


def test_strategist_does_not_see_revision_tools(
    enable_agent_chat_revision_tools: None,
) -> None:
    names = {
        tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    }
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME not in names
    assert names == set()


def test_researcher_analyst_critic_denied(
    enable_agent_chat_revision_tools: None,
) -> None:
    for agent_type in (AgentType.RESEARCHER, AgentType.ANALYST, AgentType.CRITIC):
        assert list_tools_for_agent_chat(get_tool_registry(), agent_type) == []


def test_chat_profile_excludes_approve_schedule_publish(
    enable_agent_chat_revision_tools: None,
) -> None:
    names = {
        tool.name
        for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER)
    }
    for forbidden in (
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
    ):
        assert forbidden not in names


def test_campaign_revision_max_assets_constant() -> None:
    assert AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS == 20


def test_success_revises_draft_asset_via_chat(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_revision_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    asset_id = _create_draft_asset(
        client,
        auth_headers,
        project_id,
        campaign_id=campaign_id,
    )
    revised_body = "Продающий текст: скидка 20% до пятницы. Жми кнопку в боте."

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

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "message": "Перепиши этот пост более продающе",
            "campaign_id": campaign_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revised_assets"] is not None
    assert len(body["revised_assets"]) == 1
    assert body["revised_assets"][0]["asset_id"] == asset_id
    assert body["revised_assets"][0]["version"] >= 1
    assert "Review Queue" in body["assistant_message"]["content"]
    assert "Черновик" in body["assistant_message"]["content"]

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["status"] == ContentAssetStatus.DRAFT.value
    assert asset["body"] == revised_body
    assert asset.get("approved_at") is None


def test_no_publication_jobs_after_revision(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_revision_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

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
            "Revised body for job check.",
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

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        assert [i for i in items if i.get("campaign_id") == campaign_id] == []


@pytest.mark.asyncio
async def test_audit_log_records_revision_tool(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_revision_tools: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

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
            "Audit revision body.",
        )
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Improve post", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()

    owner_id = UUID(body["session"]["owner_id"])
    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner_id,
        UUID(body["agent_run_id"]),
    )
    revision_logs = [
        log for log in logs if log.tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
    ]
    assert len(revision_logs) == 1
    assert revision_logs[0].status == "succeeded"
    preview = revision_logs[0].result_preview or {}
    assert preview.get("asset_id") == asset_id
    assert isinstance(preview.get("current_version_number"), int)


def test_structured_response_without_revised_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json().get("revised_assets") is None

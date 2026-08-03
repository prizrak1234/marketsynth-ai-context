"""Agent chat campaign_plan_draft.generate_assets tests (Phase AI.5)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import AgentType
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES,
    agent_chat_generate_assets_tools_enabled,
    list_tools_for_agent_chat,
)
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import (
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES,
    is_real_write_executable,
)
from fastapi.testclient import TestClient


def _sample_plan_payload(*, item_count: int = 3) -> dict:
    return {
        "goal": "Telegram launch",
        "target_audience": "SMB owners",
        "key_message": "Launch in Telegram",
        "content_items": [
            {
                "title": f"Item {index}",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": f"Notes {index}",
            }
            for index in range(item_count)
        ],
    }


@pytest.fixture
def enable_agent_chat_generate_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("TOOLS_PROVIDER_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def generate_flag_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED", "true")
    monkeypatch.setenv("AGENT_CHAT_TOOLS_ENABLED", "false")
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Generate Assets"}, headers=headers)
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
            "title": "June plan",
            "plan_payload": _sample_plan_payload(item_count=item_count),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _mock_generate_assets_tool_call(campaign_id: str, draft_id: str) -> dict:
    return {
        "id": "call_chat_generate",
        "type": "function",
        "function": {
            "name": CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
            "arguments": {
                "campaign_id": campaign_id,
                "draft_id": draft_id,
            },
        },
    }


def test_generate_assets_flag_off_hides_tool(generate_flag_only: None) -> None:
    assert agent_chat_generate_assets_tools_enabled() is False
    tools = list_tools_for_agent_chat(get_tool_registry(), AgentType.ORCHESTRATOR)
    assert tools == []
    assert is_real_write_executable(CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME) is False


def test_allowed_only_orchestrator_and_content_planner(
    enable_agent_chat_generate_tools: None,
) -> None:
    assert agent_chat_generate_assets_tools_enabled() is True
    for agent_type in CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES:
        names = {
            tool.name for tool in list_tools_for_agent_chat(get_tool_registry(), agent_type)
        }
        assert names == set(AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES)
    strategist_tools = list_tools_for_agent_chat(get_tool_registry(), AgentType.STRATEGIST)
    assert strategist_tools == []


def test_success_creates_draft_assets_via_chat(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_generate_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    campaign_id = _create_campaign(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)

    original_build = build_agent_chat_run_input_payload

    def _build_with_mock(*, prompt, project_id, workflow_context):
        payload = original_build(
            prompt=prompt,
            project_id=project_id,
            workflow_context=workflow_context,
        )
        payload["mock_tool_call"] = _mock_generate_assets_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={
            "message": "Разложи план в черновики",
            "campaign_id": campaign_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generated_assets"] is not None
    assert body["generated_assets"]["campaign_id"] == campaign_id
    assert body["generated_assets"]["draft_id"] == draft_id
    assert body["generated_assets"]["created_count"] == 3
    assert body["generated_assets"]["already_generated"] is False
    assert len(body["generated_assets"]["asset_ids"]) == 3
    assert "Черновики созданы: 3." in body["assistant_message"]["content"]
    assert "Review Queue" in body["assistant_message"]["content"]

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers)
    assert assets.status_code == 200
    campaign_assets = [item for item in assets.json() if item.get("campaign_id") == campaign_id]
    assert len(campaign_assets) == 3
    assert all(item["status"] == ContentAssetStatus.DRAFT.value for item in campaign_assets)


def test_idempotent_second_call(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_generate_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

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
        payload["mock_tool_call"] = _mock_generate_assets_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    first = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate assets", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    assert first["generated_assets"]["created_count"] == 3

    second = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate again", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    assert second["generated_assets"]["already_generated"] is True
    assert second["generated_assets"]["created_count"] == 0
    assert "уже были созданы ранее" in second["assistant_message"]["content"]

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers)
    campaign_assets = [item for item in assets.json() if item.get("campaign_id") == campaign_id]
    assert len(campaign_assets) == 3


def _project_owner_id(client: TestClient, headers: dict[str, str], project_id: str) -> UUID:
    project = client.get(f"/projects/{project_id}", headers=headers).json()
    return UUID(project["owner_id"])


@pytest.mark.asyncio
async def test_partial_state_error_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_generate_tools: None,
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

    owner_id = _project_owner_id(client, auth_headers, project_id)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_partial",
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


def test_no_jobs_created(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_generate_tools: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

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
        payload["mock_tool_call"] = _mock_generate_assets_tool_call(campaign_id, draft_id)
        return payload

    monkeypatch.setattr(
        "app.services.agent_chat_service.build_agent_chat_run_input_payload",
        _build_with_mock,
    )

    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Generate", "campaign_id": campaign_id},
        headers=auth_headers,
    )

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    if calendar.status_code == 200:
        payload = calendar.json()
        items = payload if isinstance(payload, list) else payload.get("items", [])
        campaign_jobs = [item for item in items if item.get("campaign_id") == campaign_id]
        assert campaign_jobs == []


@pytest.mark.asyncio
async def test_audit_log_writes(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_agent_chat_generate_tools: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session,
) -> None:
    from app.services.agent_chat_service import build_agent_chat_run_input_payload

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
        payload["mock_tool_call"] = _mock_generate_assets_tool_call(campaign_id, draft_id)
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

    owner_id = UUID(body["session"]["owner_id"])
    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner_id,
        UUID(body["agent_run_id"]),
    )
    generate_logs = [
        log for log in logs if log.tool_name == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME
    ]
    assert len(generate_logs) == 1
    assert generate_logs[0].status == "succeeded"
    assert generate_logs[0].result_preview.get("created_count") == 3


def test_project_id_forbidden_in_tool_arguments(
    enable_agent_chat_generate_tools: None,
) -> None:
    from app.tools.errors import ToolValidationError
    from app.tools.executors.campaign_plan_draft_generate_assets import (
        parse_campaign_plan_draft_generate_assets_arguments,
    )

    with pytest.raises(ToolValidationError, match="project_id"):
        parse_campaign_plan_draft_generate_assets_arguments(
            {
                "project_id": str(uuid4()),
                "campaign_id": str(uuid4()),
                "draft_id": str(uuid4()),
            },
        )


def test_structured_response_without_generated_assets_field(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("generated_assets") is None

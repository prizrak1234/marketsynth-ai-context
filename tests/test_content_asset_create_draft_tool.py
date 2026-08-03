"""Phase 4.2 — content_asset.create_draft write tool with safety gate."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate, TaskCreate
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.audit_preview import build_audit_preview
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.content_asset_create_draft import (
    parse_content_asset_create_draft_arguments,
)
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.permissions import WRITE_TOOL_NAMES
from app.tools.registry import get_tool_registry
from app.tools.result_contracts import ToolExecutionErrorCode
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def enable_create_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(client: TestClient, enable_create_draft: None) -> TestClient:
    """Ensure write-tool env vars apply before HTTP client / app settings are read."""
    get_settings.cache_clear()
    return client


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(
    *,
    owner_id,
    project_id,
    agent_id,
    agent_type: AgentType = AgentType.COPYWRITER,
    agent_run_id=None,
    task_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=agent_run_id or uuid4(),
        task_id=task_id,
    )


async def _seed_copywriter_project(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Write Tool Project {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    return owner, project, agent


def test_write_tool_not_attached_when_globally_disabled() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.COPYWRITER)
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in {tool.name for tool in tools}


def test_write_tool_disabled_by_default_in_settings() -> None:
    settings = get_settings()
    assert settings.agent_write_tools_enabled is False
    assert settings.agent_write_tool_content_asset_create_draft_enabled is False


@pytest.mark.asyncio
async def test_disabled_write_tool_call_returns_permission_denied(
    db_session: AsyncSession,
) -> None:
    owner, project, agent = await _seed_copywriter_project(db_session, telegram_id=9701)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_denied",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "email",
                "title": "Draft",
                "body": "Hello",
            },
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "write_tool_disabled"


@pytest.mark.asyncio
async def test_enabled_write_tool_visible_for_allowed_agent_types(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    registry = get_tool_registry()
    copywriter_tools = {tool.name for tool in registry.list_for_agent(AgentType.COPYWRITER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in copywriter_tools
    analyst_tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.ANALYST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in analyst_tools


@pytest.mark.asyncio
async def test_analyst_cannot_use_create_draft(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9702))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Analyst write"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.ANALYST),
    )
    assert agent is not None
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_analyst_write",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={"type": "email", "title": "Nope", "body": "text"},
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.ANALYST,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "tool_not_allowed_for_agent_type"


@pytest.mark.asyncio
async def test_create_draft_creates_draft_asset(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent = await _seed_copywriter_project(db_session, telegram_id=9703)
    task = await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Write draft task",
        ),
    )
    assert task is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=task.id,
        input_payload={"prompt": "draft"},
        metadata={},
    )
    assert run is not None
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_ok",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "telegram_post",
                "title": "Launch post",
                "body": "Hello founders",
            },
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
            task_id=task.id,
        ),
    )
    assert result.status == "succeeded"
    asset = _tool_data(result)["asset"]
    assert asset["status"] == "draft"
    assert asset["type"] == "telegram_post"
    assert "body" not in asset

    row = await ContentAssetRepository(db_session).get_by_id_for_owner(
        UUID(asset["id"]),
        owner.id,
        project.id,
    )
    assert row is not None
    assert row.status.value == "draft"
    assert row.agent_run_id == run.id
    assert row.task_id == task.id


def test_status_argument_rejected() -> None:
    with pytest.raises(ToolValidationError, match="does not accept argument: status"):
        parse_content_asset_create_draft_arguments(
            {
                "type": "email",
                "title": "T",
                "body": "B",
                "status": "approved",
            },
        )


def test_owner_id_and_project_id_arguments_rejected() -> None:
    with pytest.raises(ToolValidationError, match="owner_id"):
        parse_content_asset_create_draft_arguments(
            {
                "type": "email",
                "title": "T",
                "body": "B",
                "owner_id": str(uuid4()),
            },
        )


@pytest.mark.asyncio
async def test_body_over_max_rejected_not_persisted(
    db_session: AsyncSession,
    enable_create_draft: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOL_BODY_MAX_CHARS", "100")
    get_settings.cache_clear()
    owner, project, agent = await _seed_copywriter_project(db_session, telegram_id=9704)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_big_body",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "email",
                "title": "Big",
                "body": "x" * 200,
            },
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value
    listed = await ContentAssetRepository(db_session).list_by_project(
        owner.id,
        project.id,
    )
    assert listed == []
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_archived_brief_rejected(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent = await _seed_copywriter_project(db_session, telegram_id=9705)
    brief = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title="Archived parent",
    )
    assert brief is not None
    await MarketingBriefService(db_session).archive(owner.id, project.id, brief.id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_archived",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "brief_id": str(brief.id),
                "type": "email",
                "title": "Child",
                "body": "text",
            },
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


@pytest.mark.asyncio
async def test_brief_ownership_enforced(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner_a, project_a, agent_a = await _seed_copywriter_project(db_session, telegram_id=9706)
    owner_b = await UserRepository(db_session).create(UserTable(telegram_id=9707))
    project_b = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner_b.id, name="Other"),
    )
    agent_b = await AgentService(db_session).create_agent(
        owner_b.id,
        AgentCreateRequest(project_id=project_b.id, type=AgentType.COPYWRITER),
    )
    assert agent_b is not None
    brief = await MarketingBriefService(db_session).create(
        owner_a.id,
        project_a.id,
        title="Owned brief",
    )
    assert brief is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_brief",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "brief_id": str(brief.id),
                "type": "email",
                "title": "X",
                "body": "Y",
            },
        ),
        _context(owner_id=owner_b.id, project_id=project_b.id, agent_id=agent_b.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] in {
        ToolExecutionErrorCode.NOT_FOUND.value,
        ToolExecutionErrorCode.PERMISSION_DENIED.value,
    }


@pytest.mark.asyncio
async def test_result_and_audit_previews_exclude_full_body(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent = await _seed_copywriter_project(db_session, telegram_id=9708)
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "audit"},
        metadata={},
    )
    assert run is not None
    secret = "super-secret-body-" + ("z" * 500)
    tool_call = ToolCall(
        id="call_cd_audit",
        name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
        arguments={"type": "email", "title": "Audit", "body": secret},
    )
    context = _context(
        owner_id=owner.id,
        project_id=project.id,
        agent_id=agent.id,
        agent_run_id=run.id,
    )
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    result = await executor.execute(tool_call, context)
    preview = build_audit_preview(tool_call, result)
    serialized = json.dumps(preview.arguments_preview) + json.dumps(preview.result_preview)
    assert secret not in serialized
    assert preview.arguments_preview.get("body_length") == len(secret)
    assert preview.result_preview.get("asset_id") is not None
    assert "body" not in preview.arguments_preview

    await db_session.commit()
    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].execution_mode == "write"
    assert logs[0].tool_name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
    assert secret not in json.dumps(logs[0].arguments_preview)


def test_write_tool_names_include_create_draft() -> None:
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in WRITE_TOOL_NAMES


def test_agent_run_executor_flow_create_draft_when_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Create Draft"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "draft post",
                "mock_tool_call": {
                    "id": "call_flow_cd",
                    "type": "function",
                    "function": {
                        "name": "content_asset.create_draft",
                        "arguments": {
                            "type": "telegram_post",
                            "title": "Flow draft",
                            "body": "flow-secret-body-content",
                        },
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["content_asset.create_draft"],
    }
    assert "flow-secret-body-content" not in json.dumps(body["output_payload"])


def test_langgraph_path_create_draft_when_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Graph Create Draft"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "graph draft",
                "mock_tool_call": {
                    "id": "call_graph_cd",
                    "type": "function",
                    "function": {
                        "name": "content_asset.create_draft",
                        "arguments": {
                            "type": "email",
                            "title": "Graph draft",
                            "body": "graph-secret",
                        },
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    assert "content_asset.create_draft" in body["output_payload"]["tools"]["tool_names"]
    assert "graph-secret" not in json.dumps(body["output_payload"])


def test_failed_create_draft_still_allows_llm_follow_up(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Failed write follow-up"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "bad draft",
                "mock_tool_call": {
                    "id": "call_fail_cd",
                    "type": "function",
                    "function": {
                        "name": "content_asset.create_draft",
                        "arguments": {
                            "type": "email",
                            "title": "Bad",
                            "body": "x",
                            "status": "approved",
                        },
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock copywriter final answer after tools"
    assert body["output_payload"]["tools"]["failed_count"] == 1

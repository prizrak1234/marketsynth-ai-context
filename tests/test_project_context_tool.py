"""project_context.get read-only tool execution tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType, MemoryLayer
from app.schemas.crud import AgentCreateRequest, MemoryItemCreate, ProjectCreate, TaskCreate
from app.services.agents import AgentService
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.tools.audit_preview import build_result_preview
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.project_context_get import (
    PROJECT_CONTEXT_MAX_TASK_LIMIT,
    parse_project_context_get_arguments,
)
from app.tools.openai_schema import tool_definition_to_openai_tool
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS
from app.tools.registry import PROJECT_CONTEXT_GET_TOOL, get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(
    *,
    owner_id,
    project_id,
    agent_id,
    agent_type: AgentType = AgentType.RESEARCHER,
    agent_run_id=None,
    request_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=agent_run_id or uuid4(),
        request_id=request_id or uuid4(),
    )


def test_registry_exposes_project_context_get() -> None:
    from tests.researcher_tool_names import RESEARCHER_READ_ONLY_TOOL_NAMES

    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == RESEARCHER_READ_ONLY_TOOL_NAMES


def test_openai_schema_is_valid() -> None:
    converted = tool_definition_to_openai_tool(PROJECT_CONTEXT_GET_TOOL)
    assert converted["function"]["name"] == "project_context.get"
    assert converted["function"]["parameters"]["additionalProperties"] is False


def test_tool_rejects_model_provided_project_id() -> None:
    with pytest.raises(ToolValidationError, match="does not accept argument: project_id"):
        parse_project_context_get_arguments({"project_id": str(uuid4())})


@pytest.mark.asyncio
async def test_successful_read_returns_current_project(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9301))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Context Project", description="Desc"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_pc_1", name="project_context.get", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert result.status == "succeeded"
    data = _tool_data(result)
    assert data["project"]["id"] == str(project.id)
    assert data["project"]["name"] == "Context Project"
    assert data["project"]["description"] == "Desc"
    assert "config" not in json.dumps(data)


@pytest.mark.asyncio
async def test_cannot_read_another_owner_project(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9302))
    other = await UserRepository(db_session).create(UserTable(telegram_id=9303))
    owner_project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Owner Project"),
    )
    other_project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=other.id, name="Other Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=owner_project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_pc_2", name="project_context.get", arguments={}),
        _context(owner_id=owner.id, project_id=other_project.id, agent_id=agent.id),
    )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == "not_found"
    assert result.metadata.get("reason") == "project_not_found"


@pytest.mark.asyncio
async def test_includes_active_agents_when_enabled(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9304))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Agents Project"),
    )
    agent_service = AgentService(db_session)
    primary = await agent_service.create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER, name="Primary"),
    )
    await agent_service.create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST, name="Planner"),
    )
    assert primary is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_pc_3", name="project_context.get", arguments={"include_agents": True}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=primary.id),
    )

    data = _tool_data(result)
    assert len(data["active_agents"]) == 2
    assert all("config" not in agent for agent in data["active_agents"])


@pytest.mark.asyncio
async def test_excludes_archived_agents(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9305))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Archived Agents Project"),
    )
    agent_service = AgentService(db_session)
    active = await agent_service.create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER, name="Active"),
    )
    archived = await agent_service.create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER, name="Old"),
    )
    assert active is not None and archived is not None
    await agent_service.archive_agent(archived.id, owner.id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_pc_4", name="project_context.get", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=active.id),
    )

    data = _tool_data(result)
    agent_ids = {item["id"] for item in data["active_agents"]}
    assert str(archived.id) not in agent_ids


@pytest.mark.asyncio
async def test_includes_recent_tasks_limited_by_task_limit(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9306))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Tasks Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    tasks = TaskService(db_session)
    for index in range(6):
        await tasks.create(
            TaskCreate(
                project_id=project.id,
                agent_id=agent.id,
                title=f"Task {index}",
                input_payload={"prompt": f"secret-input-{index}"},
            ),
        )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_pc_5",
            name="project_context.get",
            arguments={"include_agents": False, "task_limit": 3},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert len(data["recent_tasks"]) == 3
    serialized = json.dumps(data["recent_tasks"])
    assert "secret-input" not in serialized
    assert "input_payload" not in serialized


def test_task_limit_max_10_enforced() -> None:
    options = parse_project_context_get_arguments({"task_limit": 99})
    assert options.task_limit == PROJECT_CONTEXT_MAX_TASK_LIMIT


@pytest.mark.asyncio
async def test_memory_summary_disabled_by_default(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9307))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Memory Default Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    await MemoryService(db_session).create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="note:1",
            content="Hidden by default",
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_pc_6", name="project_context.get", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert data["recent_memory_summary"] == []


@pytest.mark.asyncio
async def test_memory_summary_does_not_expose_full_content(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9308))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Memory Preview Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    secret = "X" * 500
    await MemoryService(db_session).create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="note:secret",
            content=secret,
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_pc_7",
            name="project_context.get",
            arguments={
                "include_agents": False,
                "include_recent_tasks": False,
                "include_memory_summary": True,
            },
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    preview = data["recent_memory_summary"][0]["content_preview"]
    assert secret not in preview
    assert len(preview) <= 180


@pytest.mark.asyncio
async def test_audit_log_created_on_success(db_session: AsyncSession) -> None:
    from app.services.tool_execution_log_service import ToolExecutionLogService

    owner = await UserRepository(db_session).create(UserTable(telegram_id=9309))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Audit Success Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(id="call_pc_8", name="project_context.get", arguments={}),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].tool_name == "project_context.get"
    assert logs[0].status == "succeeded"
    assert "Hidden by default" not in json.dumps(logs[0].result_preview)


@pytest.mark.asyncio
async def test_audit_log_created_on_tool_failure(db_session: AsyncSession) -> None:
    from app.services.tool_execution_log_service import ToolExecutionLogService

    owner = await UserRepository(db_session).create(UserTable(telegram_id=9310))
    other = await UserRepository(db_session).create(UserTable(telegram_id=9311))
    owner_project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Owner Only"),
    )
    other_project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=other.id, name="Audit Fail Project"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=owner_project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    context = _context(owner_id=owner.id, project_id=other_project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(id="call_pc_9", name="project_context.get", arguments={}),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].status == "failed"


def test_result_preview_is_compact_and_sanitized(db_session) -> None:
    del db_session
    from app.tools.contracts import ToolResult

    preview = build_result_preview(
        ToolResult(
            call_id="call_preview",
            name="project_context.get",
            status="succeeded",
            output={
                "ok": True,
                "tool": "project_context.get",
                "data": {
                    "project": {"id": "p1", "name": "Demo"},
                    "active_agents": [{"id": "a1", "config": {"secret": "nope"}}],
                    "recent_tasks": [],
                    "recent_memory_summary": [],
                    "count": 1,
                },
                "meta": {"truncated": False, "items_count": 1},
            },
            metadata={"result_count": 1},
        ),
    )
    assert preview["items_count"] == 1
    assert "secret" not in json.dumps(preview)


def test_real_executable_allow_list_contains_project_context_get() -> None:
    assert "project_context.get" in REAL_READ_ONLY_EXECUTABLE_TOOLS


def test_agent_run_executor_flow_injects_project_context_result(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Project"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {"prompt": "context", "force_tool_call": "project_context.get"},
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"
    assert body["output_payload"]["tool_audit"]["logged_count"] == 1

    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert logs[0]["tool_name"] == "project_context.get"
    assert logs[0]["status"] == "succeeded"


@patch(
    "app.services.tool_execution_log_service.ToolExecutionLogService.record_execution",
    new_callable=AsyncMock,
)
def test_audit_failure_does_not_fail_agent_run_for_project_context(
    mock_record: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_record.side_effect = RuntimeError("audit unavailable")
    project_id = client.post(
        "/projects",
        json={"name": "Audit Fail Flow"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {"prompt": "context", "force_tool_call": "project_context.get"},
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["output_payload"]["tool_audit"]["failed_to_log_count"] == 1

"""task.get and task.list_recent read-only tool execution tests."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType, TaskStatus
from app.schemas.crud import AgentCreateRequest, ProjectCreate, TaskCreate
from app.services.agents import AgentService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor, build_tools_run_summary
from app.tools.executors.task_get import parse_task_get_arguments
from app.tools.executors.task_list_recent import (
    TASK_LIST_RECENT_MAX_LIMIT,
    parse_task_list_recent_arguments,
)
from app.tools.openai_schema import tool_definition_to_openai_tool
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS
from app.tools.registry import TASK_GET_TOOL, TASK_LIST_RECENT_TOOL, get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.researcher_tool_names import RESEARCHER_READ_ONLY_TOOL_NAMES as EXPECTED_TOOL_NAMES


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


async def _seed_project_with_agent(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Task Tool Project {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    return owner, project, agent


def test_registry_exposes_task_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == EXPECTED_TOOL_NAMES


def test_openai_schemas_are_valid() -> None:
    for tool in (TASK_GET_TOOL, TASK_LIST_RECENT_TOOL):
        converted = tool_definition_to_openai_tool(tool)
        assert converted["function"]["name"] == tool.name
        assert converted["function"]["parameters"]["additionalProperties"] is False


@pytest.mark.asyncio
async def test_task_get_returns_envelope_ok_true(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9501)
    task = await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Read me",
            input_payload={"prompt": "secret-input"},
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tg_1", name="task.get", arguments={"task_id": str(task.id)}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert result.status == "succeeded"
    assert result.output["tool"] == "task.get"
    data = _tool_data(result)
    assert data["task"]["id"] == str(task.id)
    assert data["task"]["title"] == "Read me"


@pytest.mark.asyncio
async def test_task_get_does_not_expose_input_payload(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9502)
    task = await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Secret task",
            input_payload={"prompt": "super-secret-input-payload"},
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tg_2", name="task.get", arguments={"task_id": str(task.id)}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    serialized = json.dumps(_tool_data(result))
    assert "super-secret-input-payload" not in serialized
    assert "input_payload" not in serialized


@pytest.mark.asyncio
async def test_task_get_includes_metadata_only_when_requested(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9503)
    task = await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Metadata task",
            input_payload={"prompt": "x"},
        ),
    )
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)

    without_metadata = await executor.execute(
        ToolCall(
            id="call_tg_3a",
            name="task.get",
            arguments={"task_id": str(task.id), "include_metadata": False},
        ),
        context,
    )
    assert "metadata" not in _tool_data(without_metadata)["task"]

    with_metadata = await executor.execute(
        ToolCall(
            id="call_tg_3b",
            name="task.get",
            arguments={"task_id": str(task.id), "include_metadata": True},
        ),
        context,
    )
    assert "metadata" in _tool_data(with_metadata)["task"]


@pytest.mark.asyncio
async def test_task_get_not_found_for_missing_task(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9504)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tg_4", name="task.get", arguments={"task_id": str(uuid4())}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert result.status == "failed"
    assert result.output["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_task_get_cannot_read_another_owner_project_task(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9505))
    other = await UserRepository(db_session).create(UserTable(telegram_id=9506))
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
    other_task = await TaskService(db_session).create(
        TaskCreate(
            project_id=other_project.id,
            agent_id=agent.id,
            title="Other owner task",
            input_payload={"prompt": "secret"},
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tg_5", name="task.get", arguments={"task_id": str(other_task.id)}),
        _context(owner_id=owner.id, project_id=owner_project.id, agent_id=agent.id),
    )

    assert result.status == "failed"
    assert result.output["error"]["code"] == "permission_denied"


def test_task_get_rejects_model_provided_project_id() -> None:
    with pytest.raises(ToolValidationError, match="does not accept argument: project_id"):
        parse_task_get_arguments({"task_id": str(uuid4()), "project_id": str(uuid4())})


@pytest.mark.asyncio
async def test_task_list_recent_returns_newest_first(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9507)
    tasks = TaskService(db_session)
    first = await tasks.create(
        TaskCreate(project_id=project.id, agent_id=agent.id, title="First"),
    )
    second = await tasks.create(
        TaskCreate(project_id=project.id, agent_id=agent.id, title="Second"),
    )
    third = await tasks.create(
        TaskCreate(project_id=project.id, agent_id=agent.id, title="Third"),
    )
    assert first is not None and second is not None and third is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tl_1", name="task.list_recent", arguments={"limit": 3}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Third", "Second", "First"]


def test_task_list_recent_enforces_limit_max_10() -> None:
    options = parse_task_list_recent_arguments({"limit": 99})
    assert options.limit == TASK_LIST_RECENT_MAX_LIMIT


@pytest.mark.asyncio
async def test_task_list_recent_filters_by_status(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9508)
    tasks = TaskService(db_session)
    pending = await tasks.create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Pending task",
            status=TaskStatus.PENDING,
        ),
    )
    completed = await tasks.create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Completed task",
            status=TaskStatus.COMPLETED,
        ),
    )
    assert pending is not None and completed is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_tl_2",
            name="task.list_recent",
            arguments={"status": "completed", "limit": 10},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    items = _tool_data(result)["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Completed task"
    assert items[0]["status"] == TaskStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_task_list_recent_does_not_expose_input_payload(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9509)
    await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="List secret",
            input_payload={"prompt": "list-secret-input"},
        ),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tl_3", name="task.list_recent", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    serialized = json.dumps(_tool_data(result))
    assert "list-secret-input" not in serialized
    assert "input_payload" not in serialized


@pytest.mark.asyncio
async def test_task_list_recent_metadata_disabled_by_default(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9510)
    await TaskService(db_session).create(
        TaskCreate(project_id=project.id, agent_id=agent.id, title="Default metadata"),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_tl_4", name="task.list_recent", arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert "metadata" not in _tool_data(result)["items"][0]


@pytest.mark.asyncio
async def test_audit_log_created_on_success(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9511)
    task = await TaskService(db_session).create(
        TaskCreate(project_id=project.id, agent_id=agent.id, title="Audit success"),
    )
    assert task is not None
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(id="call_tg_audit_ok", name="task.get", arguments={"task_id": str(task.id)}),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].tool_name == "task.get"
    assert logs[0].status == "succeeded"
    assert logs[0].arguments_preview["task_id"] == str(task.id)
    assert "owner_id" not in logs[0].arguments_preview
    assert logs[0].result_preview["ok"] is True


@pytest.mark.asyncio
async def test_audit_log_created_on_failure(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9512)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(id="call_tg_audit_fail", name="task.get", arguments={"task_id": str(uuid4())}),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].result_preview["error_code"] == "not_found"


def test_agent_run_executor_flow_executes_task_get(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Task Get"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    task_id = client.post(
        "/tasks",
        json={
            "project_id": project_id,
            "agent_id": agent_id,
            "title": "Flow task",
            "input_payload": {"prompt": "flow-secret"},
        },
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "get task",
                "mock_tool_call": {
                    "id": "call_flow_get",
                    "type": "function",
                    "function": {
                        "name": "task.get",
                        "arguments": {"task_id": task_id},
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
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"
    assert body["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["task.get"],
    }
    assert "flow-secret" not in json.dumps(body["output_payload"])


def test_agent_run_executor_flow_executes_task_list_recent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Task List"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        "/tasks",
        json={
            "project_id": project_id,
            "agent_id": agent_id,
            "title": "Listed task",
            "input_payload": {"prompt": "listed-secret"},
        },
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "list tasks",
                "mock_tool_call": {
                    "id": "call_flow_list",
                    "type": "function",
                    "function": {
                        "name": "task.list_recent",
                        "arguments": {"limit": 5},
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
        "tool_names": ["task.list_recent"],
    }


def test_tool_summary_counts_success_and_failure() -> None:
    from app.tools.contracts import ToolResult
    from app.tools.result_builder import build_tool_error, build_tool_success
    from app.tools.result_contracts import ToolExecutionErrorCode

    summary = build_tools_run_summary(
        [
            ToolResult(
                call_id="ok",
                name="task.get",
                status="succeeded",
                output=build_tool_success("task.get", {"task": {}, "count": 1}),
            ),
            ToolResult(
                call_id="fail",
                name="task.get",
                status="failed",
                output=build_tool_error(
                    "task.get",
                    code=ToolExecutionErrorCode.NOT_FOUND,
                    message="Task not found",
                ),
            ),
        ],
    )
    assert summary == {
        "executed_count": 1,
        "failed_count": 1,
        "tool_names": ["task.get"],
    }


def test_real_executable_allow_list_contains_task_tools() -> None:
    assert "task.get" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert "task.list_recent" in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert len(REAL_READ_ONLY_EXECUTABLE_TOOLS) == 12

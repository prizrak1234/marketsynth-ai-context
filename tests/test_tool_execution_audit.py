"""Phase 2.14 — tool execution audit logging tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType, MemoryLayer
from app.schemas.crud import MemoryItemCreate, ProjectCreate
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.audit_preview import (
    MAX_ARGUMENT_STRING_LENGTH,
    build_arguments_preview,
    build_result_preview,
)
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext, ToolResult
from app.tools.executor import SafeNoOpToolExecutor, build_tools_run_summary
from app.tools.registry import MEMORY_SEARCH_TOOL, ToolRegistry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _create_project(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Audit Project",
) -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    agent_id: str,
    *,
    input_payload: dict | None = None,
) -> dict:
    response = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": input_payload or {"prompt": "audit test"},
            "metadata": {"source": "audit-test"},
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _register_test_tool(name: str) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name=name,
            description="Test tool",
            parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            enabled=True,
        ),
    )
    return registry


def _context(**kwargs) -> ToolExecutionContext:
    defaults = {
        "owner_id": uuid4(),
        "project_id": uuid4(),
        "agent_id": uuid4(),
        "agent_type": AgentType.RESEARCHER,
        "agent_run_id": uuid4(),
        "request_id": uuid4(),
    }
    defaults.update(kwargs)
    return ToolExecutionContext(**defaults)


async def _list_audit_logs(db_session: AsyncSession, context: ToolExecutionContext) -> list:
    repo = ToolExecutionLogRepository(db_session)
    return await repo.list_by_run(context.owner_id, context.agent_run_id)


@pytest.mark.asyncio
async def test_memory_search_succeeded_creates_audit_log(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9201))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Audit Memory Project"),
    )
    memory = MemoryService(db_session)
    await memory.create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="note:1",
            content="Audience insight for audit",
            metadata={"source": "test"},
        ),
    )

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        registry,
        memory_service=memory,
        audit_service=audit_service,
    )
    context = _context(owner_id=owner.id, project_id=project.id)
    await executor.execute(
        ToolCall(id="call_audit_1", name="memory.search", arguments={"query": "audience"}),
        context,
    )
    await db_session.commit()

    logs = await _list_audit_logs(db_session, context)
    assert len(logs) == 1
    assert logs[0].tool_name == "memory.search"
    assert logs[0].status == "succeeded"
    assert logs[0].execution_mode == "read_only"
    assert logs[0].result_preview["items_count"] == 1
    assert "items" not in logs[0].result_preview
    assert "Audience insight" not in json.dumps(
        {
            "arguments_preview": logs[0].arguments_preview,
            "result_preview": logs[0].result_preview,
            "error_payload": logs[0].error_payload,
        },
    )


@pytest.mark.asyncio
async def test_bad_args_create_failed_audit_log(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        registry,
        memory_service=MemoryService(db_session),
        audit_service=audit_service,
    )
    context = _context()
    await executor.execute(
        ToolCall(id="call_bad", name="memory.search", arguments={"query": "   "}),
        context,
    )
    await db_session.commit()

    logs = await _list_audit_logs(db_session, context)
    assert logs[0].status == "failed"
    assert logs[0].reason == "invalid_tool_arguments"
    assert logs[0].error_payload is not None
    assert "safe_message" in logs[0].error_payload


@pytest.mark.asyncio
async def test_write_tool_call_creates_skipped_audit_log(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="memory.write",
            description="Write memory",
            parameters_schema={"type": "object"},
            enabled=True,
        ),
    )
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(registry, audit_service=audit_service)
    context = _context()
    await executor.execute(
        ToolCall(id="call_write", name="memory.write", arguments={"content": "secret"}),
        context,
    )
    await db_session.commit()

    logs = await _list_audit_logs(db_session, context)
    assert logs[0].status == "skipped"
    assert logs[0].reason == "tool_not_allowed"
    assert logs[0].execution_mode == "no_op"


@pytest.mark.asyncio
async def test_noop_tool_creates_skipped_audit_log(db_session: AsyncSession) -> None:
    registry = _register_test_tool("search_brief")
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(registry, audit_service=audit_service)
    context = _context()
    await executor.execute(
        ToolCall(id="call_noop", name="search_brief", arguments={"query": "x"}),
        context,
    )
    await db_session.commit()

    logs = await _list_audit_logs(db_session, context)
    assert logs[0].status == "skipped"
    assert logs[0].reason == "tool_execution_disabled"
    assert logs[0].execution_mode == "no_op"


def test_arguments_preview_is_sanitized_and_truncated() -> None:
    long_query = "q" * (MAX_ARGUMENT_STRING_LENGTH + 50)
    preview = build_arguments_preview(
        {
            "query": long_query,
            "api_key": "sk-secret",
        },
    )
    assert preview["api_key"] == "[REDACTED]"
    assert len(preview["query"]) <= MAX_ARGUMENT_STRING_LENGTH + len("...[truncated]")


def test_result_preview_excludes_memory_items_content() -> None:
    from app.tools.result_builder import build_tool_success

    preview = build_result_preview(
        ToolResult(
            call_id="call_1",
            name="memory.search",
            status="succeeded",
            output=build_tool_success(
                "memory.search",
                {"count": 1, "items": [{"content_preview": "SECRET_MEMORY_BODY"}]},
            ),
            metadata={"execution_mode": "read_only", "result_count": 1},
        ),
    )
    assert preview["items_count"] == 1
    assert "items" not in preview
    assert "SECRET_MEMORY_BODY" not in json.dumps(preview)


@patch(
    "app.services.tool_execution_log_service.ToolExecutionLogService.record_execution",
    new_callable=AsyncMock,
)
def test_audit_failure_does_not_fail_agent_run(
    mock_record: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_record.side_effect = RuntimeError("audit db down")

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tool_audit"]["failed_to_log_count"] == 1
    assert body["output_payload"]["tool_audit"]["logged_count"] == 0


def test_get_agent_run_tool_executions_returns_owned_logs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "audit:1",
            "content": "audit memory note",
            "metadata": {},
        },
        headers=auth_headers,
    )
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    execute = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert execute.status_code == 200

    response = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers)
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "memory.search"
    assert logs[0]["status"] == "succeeded"
    assert "audit memory note" not in json.dumps(logs)


def test_other_owner_gets_404_for_run_tool_executions(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    response = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=other_auth_headers)
    assert response.status_code == 404


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_project_tool_execution_filters(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_test_tool("search_brief")
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "noop",
            "mock_tool_call": {
                "id": "call_filter",
                "type": "function",
                "function": {"name": "search_brief", "arguments": {"query": "x"}},
            },
        },
    )
    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    all_logs = client.get(
        f"/projects/{project_id}/tool-executions",
        headers=auth_headers,
    )
    assert all_logs.status_code == 200
    assert len(all_logs.json()) == 1

    skipped = client.get(
        f"/projects/{project_id}/tool-executions",
        params={"status": "skipped", "tool_name": "search_brief"},
        headers=auth_headers,
    )
    assert skipped.status_code == 200
    assert len(skipped.json()) == 1

    succeeded = client.get(
        f"/projects/{project_id}/tool-executions",
        params={"status": "succeeded"},
        headers=auth_headers,
    )
    assert succeeded.status_code == 200
    assert succeeded.json() == []


def test_other_owner_gets_404_for_project_tool_executions(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.get(f"/projects/{project_id}/tool-executions", headers=other_auth_headers)
    assert response.status_code == 404


def test_tool_audit_summary_in_agent_run_output(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    tool_audit = body["output_payload"]["tool_audit"]
    assert tool_audit["logged_count"] == 1
    assert tool_audit["failed_to_log_count"] == 0
    assert body["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["memory.search"],
    }


def test_build_tools_run_summary_preserves_unique_tool_order() -> None:
    results = [
        ToolResult(
            call_id="call_1",
            name="project_context.get",
            status="succeeded",
            output={"ok": True},
        ),
        ToolResult(
            call_id="call_2",
            name="task.list_recent",
            status="succeeded",
            output={"ok": True},
        ),
        ToolResult(
            call_id="call_3",
            name="project_context.get",
            status="failed",
            output={"ok": False},
        ),
    ]
    summary = build_tools_run_summary(results)
    assert summary["tool_names"] == ["project_context.get", "task.list_recent"]
    assert summary["executed_count"] == 2
    assert summary["failed_count"] == 1


@pytest.mark.asyncio
async def test_list_by_project_filters_execution_mode_and_date_range(
    db_session: AsyncSession,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9202))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Filter Project"),
    )
    agent_id = uuid4()
    agent_run_id = uuid4()
    base = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    repo = ToolExecutionLogRepository(db_session)
    for index, (tool_name, mode, status, created_at) in enumerate(
        [
            ("memory.search", "read_only", "succeeded", base),
            ("search_brief", "no_op", "skipped", base + timedelta(hours=1)),
            ("memory.search", "read_only", "failed", base + timedelta(hours=2)),
        ],
    ):
        await repo.create(
            ToolExecutionLogTable(
                owner_id=owner.id,
                project_id=project.id,
                agent_id=agent_id,
                agent_run_id=agent_run_id,
                tool_call_id=f"call_{index}",
                tool_name=tool_name,
                status=status,
                execution_mode=mode,
                created_at=created_at,
            ),
        )
    await db_session.commit()

    read_only = await repo.list_by_project(
        owner.id,
        project.id,
        execution_mode="read_only",
    )
    assert len(read_only) == 2
    assert {row.tool_name for row in read_only} == {"memory.search"}

    middle_window = await repo.list_by_project(
        owner.id,
        project.id,
        created_from=base + timedelta(minutes=30),
        created_to=base + timedelta(hours=1, minutes=30),
    )
    assert len(middle_window) == 1
    assert middle_window[0].tool_name == "search_brief"


@pytest.mark.asyncio
async def test_list_by_project_pagination_is_stable(db_session: AsyncSession) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9203))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Pagination Project"),
    )
    agent_id = uuid4()
    agent_run_id = uuid4()
    repo = ToolExecutionLogRepository(db_session)
    base = datetime(2026, 5, 2, 12, 0, 0, tzinfo=UTC)
    for index in range(3):
        await repo.create(
            ToolExecutionLogTable(
                owner_id=owner.id,
                project_id=project.id,
                agent_id=agent_id,
                agent_run_id=agent_run_id,
                tool_call_id=f"call_page_{index}",
                tool_name=f"tool_{index}",
                status="succeeded",
                execution_mode="read_only",
                created_at=base + timedelta(minutes=index),
            ),
        )
    await db_session.commit()

    page_one = await repo.list_by_project(owner.id, project.id, limit=1, offset=0)
    page_two = await repo.list_by_project(owner.id, project.id, limit=1, offset=1)
    assert page_one[0].tool_name == "tool_2"
    assert page_two[0].tool_name == "tool_1"


def test_project_tool_execution_api_filters_execution_mode_and_dates(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, name="API Filter Project")
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    read_only = client.get(
        f"/projects/{project_id}/tool-executions",
        params={"execution_mode": "read_only"},
        headers=auth_headers,
    )
    assert read_only.status_code == 200
    assert len(read_only.json()) == 1
    assert read_only.json()[0]["execution_mode"] == "read_only"

    future = client.get(
        f"/projects/{project_id}/tool-executions",
        params={"created_from": "2099-01-01T00:00:00Z"},
        headers=auth_headers,
    )
    assert future.status_code == 200
    assert future.json() == []

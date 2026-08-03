"""memory.search read-only tool execution tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.schemas.contracts import AgentType, MemoryLayer
from app.schemas.crud import MemoryItemCreate, ProjectCreate
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor, build_tool_call_metadata
from app.tools.executors.memory_search import (
    MEMORY_SEARCH_MAX_LIMIT,
    MemorySearchToolExecutor,
    parse_memory_search_arguments,
)
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS
from app.tools.registry import MEMORY_SEARCH_TOOL, ToolRegistry, get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.researcher_tool_names import RESEARCHER_READ_ONLY_TOOL_NAMES


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(
    *,
    owner_id,
    project_id,
    agent_id,
    agent_type: AgentType = AgentType.RESEARCHER,
    request_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=uuid4(),
        request_id=request_id or uuid4(),
    )


@pytest.mark.asyncio
async def test_researcher_can_execute_memory_search(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=9101))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Memory Search Project"),
    )
    memory = MemoryService(db_session)
    await memory.create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="campaign:audience",
            content="Target audience prefers short-form video",
            metadata={"channel": "tiktok"},
        ),
    )

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=memory)
    result = await executor.execute(
        ToolCall(id="call_ms_1", name="memory.search", arguments={"query": "audience"}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=uuid4()),
    )

    assert result.status == "succeeded"
    assert result.output is not None
    data = _tool_data(result)
    assert data["count"] == 1
    assert data["items"][0]["kind"] == MemoryLayer.L1_SESSION.value
    assert result.metadata["execution_mode"] == "read_only"
    assert result.metadata["result_count"] == 1


@pytest.mark.asyncio
async def test_strategist_can_execute_memory_search(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=9102))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Strategist Memory Project"),
    )

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_2", name="memory.search", arguments={"query": "plan"}),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=uuid4(),
            agent_type=AgentType.STRATEGIST,
        ),
    )
    assert result.status == "succeeded"
    data = _tool_data(result)
    assert data == {"items": [], "count": 0}


@pytest.mark.asyncio
async def test_disabled_memory_search_tool_is_skipped(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL.model_copy(update={"enabled": False}))
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_3", name="memory.search", arguments={"query": "x"}),
        _context(owner_id=uuid4(), project_id=uuid4(), agent_id=uuid4()),
    )
    assert result.status == "skipped"
    assert result.output["reason"] == "tool_disabled"


@pytest.mark.asyncio
async def test_write_tool_remains_not_allowed(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="memory.write",
            description="Write memory",
            parameters_schema={"type": "object", "properties": {}},
            enabled=True,
            metadata={"access_mode": "write"},
        ),
    )
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_4", name="memory.write", arguments={"content": "x"}),
        _context(owner_id=uuid4(), project_id=uuid4(), agent_id=uuid4()),
    )
    assert result.status == "skipped"
    assert result.output["reason"] == "tool_not_allowed"


@pytest.mark.asyncio
async def test_bad_arguments_return_invalid_tool_arguments(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_5", name="memory.search", arguments={"query": "   "}),
        _context(owner_id=uuid4(), project_id=uuid4(), agent_id=uuid4()),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == "invalid_arguments"
    assert result.metadata["reason"] == "invalid_tool_arguments"


def test_limit_above_max_is_clamped() -> None:
    _, _, limit = parse_memory_search_arguments({"query": "hello", "limit": 100})
    assert limit == MEMORY_SEARCH_MAX_LIMIT


@pytest.mark.asyncio
async def test_other_owner_memory_is_not_returned(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    owner = await user_repo.create(UserTable(telegram_id=9103))
    other = await user_repo.create(UserTable(telegram_id=9104))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Scoped Memory Project"),
    )
    memory = MemoryService(db_session)
    await memory.create(
        MemoryItemCreate(
            user_id=other.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="secret:note",
            content="other owner secret note",
        ),
    )
    await memory.create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="owner:note",
            content="owner visible note",
        ),
    )

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    executor = SafeNoOpToolExecutor(registry, memory_service=memory)
    result = await executor.execute(
        ToolCall(id="call_ms_6", name="memory.search", arguments={"query": "note"}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=uuid4()),
    )
    assert result.status == "succeeded"
    data = _tool_data(result)
    assert data["count"] == 1
    assert data["items"][0]["content_preview"] == "owner visible note"


@pytest.mark.asyncio
async def test_no_op_tools_keep_disabled_execution(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search_brief",
            description="Search brief",
            parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            enabled=True,
        ),
    )
    executor = SafeNoOpToolExecutor(registry, memory_service=MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_7", name="search_brief", arguments={"query": "x"}),
        _context(owner_id=uuid4(), project_id=uuid4(), agent_id=uuid4()),
    )
    assert result.status == "skipped"
    assert result.output["reason"] == "tool_execution_disabled"


def test_metadata_contains_permission_policy_and_tool_executions() -> None:
    metadata = build_tool_call_metadata(
        available_tool_names=["memory.search"],
        tool_results=[],
        permission_policy={
            "agent_type": "researcher",
            "execution_mode": "no_op",
            "allowed_tool_count": 1,
        },
    )
    assert metadata["permission_policy"]["allowed_tool_count"] == 1
    assert metadata["tool_executions"] == []


@pytest.mark.asyncio
async def test_request_id_is_present_in_execution_context(db_session: AsyncSession) -> None:
    request_id = uuid4()
    executor = MemorySearchToolExecutor(MemoryService(db_session))
    result = await executor.execute(
        ToolCall(id="call_ms_8", name="memory.search", arguments={"query": "x"}),
        _context(
            owner_id=uuid4(),
            project_id=uuid4(),
            agent_id=uuid4(),
            request_id=request_id,
        ),
    )
    assert result.request_id == request_id


def test_default_registry_exposes_memory_search_for_researcher() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == RESEARCHER_READ_ONLY_TOOL_NAMES


def test_real_executable_allow_list_contains_all_read_only_tools() -> None:
    assert len(REAL_READ_ONLY_EXECUTABLE_TOOLS) == 12
    assert "memory.search" in REAL_READ_ONLY_EXECUTABLE_TOOLS


def test_dry_run_metadata_includes_permission_policy(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Memory Tool Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "hello"}},
        headers=auth_headers,
    ).json()["id"]
    client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    tools_metadata = llm_request["request_metadata"]["tools_metadata"]
    assert tools_metadata["tools_enabled"] is True
    assert tools_metadata["tool_names"] == RESEARCHER_READ_ONLY_TOOL_NAMES
    assert tools_metadata["permission_policy"]["execution_mode"] == "no_op"
    assert tools_metadata["tool_executions"] == []

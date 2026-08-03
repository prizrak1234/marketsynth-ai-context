"""Safe no-op tool executor tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.schemas.contracts import AgentType
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.registry import ToolRegistry


def _sample_tool(*, name: str = "search_brief", enabled: bool = True) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Search marketing brief snippets",
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        enabled=enabled,
    )


def _context(agent_type: AgentType = AgentType.RESEARCHER) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_known_enabled_tool_returns_skipped() -> None:
    registry = ToolRegistry()
    registry.register(_sample_tool(name="search_brief"))
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_1", name="search_brief", arguments={"query": "audience"}),
        _context(agent_type=AgentType.RESEARCHER),
    )
    assert result.status == "skipped"
    assert isinstance(result.output, dict)
    assert result.output["reason"] == "tool_execution_disabled"
    assert result.output["tool_call_id"] == "call_1"


@pytest.mark.asyncio
async def test_not_allowed_tool_returns_skipped_safe() -> None:
    registry = ToolRegistry()
    registry.register(_sample_tool(name="memory.write"))
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_5", name="memory.write", arguments={}),
        _context(agent_type=AgentType.RESEARCHER),
    )
    assert result.status == "skipped"
    assert result.output["reason"] == "tool_not_allowed"


@pytest.mark.asyncio
async def test_disabled_tool_returns_skipped_safe() -> None:
    registry = ToolRegistry()
    registry.register(_sample_tool(name="disabled_tool", enabled=False))
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_2", name="disabled_tool", arguments={}),
        _context(),
    )
    assert result.status == "skipped"
    assert result.output["reason"] == "tool_disabled"


@pytest.mark.asyncio
async def test_unknown_tool_returns_failed_safe() -> None:
    registry = ToolRegistry()
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_3", name="missing_tool", arguments={}),
        _context(),
    )
    assert result.status == "failed"
    assert result.error is not None
    assert result.error["error_type"] == "tool_not_found"


@pytest.mark.asyncio
async def test_result_is_sanitized() -> None:
    registry = ToolRegistry()
    registry.register(_sample_tool(name="search_brief"))
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_4", name="search_brief", arguments={"query": "token=sk-secret"}),
        _context(agent_type=AgentType.RESEARCHER),
    )
    assert result.status == "skipped"
    assert "sk-secret" not in str(result.output)

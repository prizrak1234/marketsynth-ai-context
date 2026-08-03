"""Tool permission matrix and access decision tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext
from app.tools.errors import ToolNotAllowedForAgentError, ToolNotFoundError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.permissions import (
    DEFAULT_TOOL_PERMISSION_MATRIX,
    READ_ONLY_TOOL_NAMES,
    WRITE_TOOL_NAMES,
    ToolAccessReasonCode,
    ToolExecutionMode,
    ToolPermissionPolicy,
    assert_tool_allowed,
    evaluate_tool_access,
    filter_tools_for_agent,
    get_tool_permission_policy,
)
from app.tools.registry import MEMORY_SEARCH_TOOL, ToolRegistry
from app.tools.result_contracts import ToolExecutionErrorCode
from app.tools.write_tool_settings import LEGACY_WRITE_TOOL_NAMES
from sqlalchemy.ext.asyncio import AsyncSession


def _tool(
    *,
    name: str = "memory.search",
    enabled: bool = True,
    access_mode: str | None = None,
    allowed_agent_types: list[AgentType] | None = None,
) -> ToolDefinition:
    metadata: dict[str, str] = {}
    if access_mode is not None:
        metadata["access_mode"] = access_mode
    return ToolDefinition(
        name=name,
        description="Test tool",
        parameters_schema={"type": "object", "properties": {}},
        enabled=enabled,
        allowed_agent_types=allowed_agent_types,
        metadata=metadata,
    )


def _context(agent_type: AgentType = AgentType.RESEARCHER) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
    )


def test_allowed_read_only_tool_passes_for_strategist() -> None:
    decision = evaluate_tool_access(
        agent_type=AgentType.STRATEGIST,
        tool_name="memory.search",
        tool=_tool(),
    )
    assert decision.allowed is True
    assert decision.reason_code == ToolAccessReasonCode.ALLOWED
    assert decision.execution_mode == ToolExecutionMode.READ_ONLY
    assert_tool_allowed(AgentType.STRATEGIST, "memory.search", tool=_tool())


def test_denied_tool_is_rejected() -> None:
    decision = evaluate_tool_access(
        agent_type=AgentType.STRATEGIST,
        tool_name="memory.write",
        tool=_tool(name="memory.write", access_mode="write"),
    )
    assert decision.allowed is False
    assert decision.reason_code in {
        ToolAccessReasonCode.WRITE_TOOL_NOT_ALLOWED,
        ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
    }
    with pytest.raises(ToolNotAllowedForAgentError, match="Write tool"):
        assert_tool_allowed(AgentType.STRATEGIST, "memory.write", tool=_tool(name="memory.write"))


def test_tool_not_in_allow_list_is_rejected() -> None:
    decision = evaluate_tool_access(
        agent_type=AgentType.STRATEGIST,
        tool_name="unknown_tool",
        tool=_tool(name="unknown_tool"),
    )
    assert decision.allowed is False
    assert decision.reason_code == ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST
    with pytest.raises(ToolNotAllowedForAgentError, match="not allowed"):
        assert_tool_allowed(AgentType.STRATEGIST, "unknown_tool", tool=_tool(name="unknown_tool"))


def test_tool_not_found_via_registry() -> None:
    registry = ToolRegistry()
    decision = evaluate_tool_access(
        agent_type=AgentType.RESEARCHER,
        tool_name="missing_tool",
        registry=registry,
    )
    assert decision.allowed is False
    assert decision.reason_code == ToolAccessReasonCode.TOOL_NOT_FOUND
    assert decision.audit_reason == "tool_not_found"


def test_tool_disabled_decision() -> None:
    decision = evaluate_tool_access(
        agent_type=AgentType.RESEARCHER,
        tool_name="memory.search",
        tool=_tool(name="memory.search", enabled=False),
    )
    assert decision.allowed is False
    assert decision.reason_code == ToolAccessReasonCode.TOOL_DISABLED
    assert decision.audit_reason == "tool_disabled"


def test_tools_disabled_for_agent_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        DEFAULT_TOOL_PERMISSION_MATRIX,
        AgentType.RESEARCHER,
        ToolPermissionPolicy(
            agent_type=AgentType.RESEARCHER,
            allowed_tools=set(READ_ONLY_TOOL_NAMES),
            denied_tools=set(WRITE_TOOL_NAMES),
            execution_mode=ToolExecutionMode.DISABLED,
        ),
    )
    decision = evaluate_tool_access(
        agent_type=AgentType.RESEARCHER,
        tool_name="memory.search",
        tool=_tool(),
    )
    assert decision.allowed is False
    assert decision.reason_code == ToolAccessReasonCode.TOOLS_DISABLED_FOR_AGENT
    assert decision.audit_reason == "tool_not_allowed"


def test_agent_type_not_allowed_on_tool_definition() -> None:
    decision = evaluate_tool_access(
        agent_type=AgentType.COPYWRITER,
        tool_name="memory.search",
        tool=_tool(allowed_agent_types=[AgentType.RESEARCHER]),
    )
    assert decision.allowed is False
    assert decision.reason_code == ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED
    assert decision.audit_reason == "tool_not_allowed"


def test_execution_mode_not_allowed_reason_code_exists() -> None:
    assert ToolAccessReasonCode.EXECUTION_MODE_NOT_ALLOWED.value == "execution_mode_not_allowed"


def test_disabled_tool_is_not_listed_for_agent() -> None:
    registry = ToolRegistry()
    registry.register(_tool(name="memory.search", enabled=False))
    registry.register(_tool(name="search_brief", enabled=True))
    tools = registry.list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == ["search_brief"]


def test_filter_tools_for_agent_excludes_write_tools_for_orchestrator() -> None:
    tools = filter_tools_for_agent(
        AgentType.ORCHESTRATOR,
        [
            _tool(name="memory.search"),
            _tool(name="memory.write", access_mode="write"),
        ],
    )
    assert [tool.name for tool in tools] == ["memory.search"]


def test_each_agent_type_has_policy() -> None:
    for agent_type in AgentType:
        policy = get_tool_permission_policy(agent_type)
        base = DEFAULT_TOOL_PERMISSION_MATRIX[agent_type]
        assert policy.agent_type == agent_type
        assert policy.execution_mode == ToolExecutionMode.NO_OP
        assert policy.denied_tools == set(LEGACY_WRITE_TOOL_NAMES)
        assert base.denied_tools == set(LEGACY_WRITE_TOOL_NAMES)


def test_orchestrator_does_not_receive_write_tools_via_registry() -> None:
    registry = ToolRegistry()
    registry.register(_tool(name="memory.search"))
    registry.register(_tool(name="memory.write", access_mode="write"))
    tools = registry.list_for_agent(AgentType.ORCHESTRATOR)
    assert [tool.name for tool in tools] == ["memory.search"]


def test_provider_tool_list_excludes_write_tools_for_researcher() -> None:
    registry = ToolRegistry()
    registry.register(_tool(name="memory.search"))
    registry.register(_tool(name="memory.write", access_mode="write"))
    tools = registry.list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == ["memory.search"]


def test_registry_validate_unknown_tool_raises_not_found() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.validate_tool_allowed("missing_tool", AgentType.RESEARCHER)


def test_read_only_tool_names_include_future_phase_tools() -> None:
    assert "memory.search" in READ_ONLY_TOOL_NAMES
    assert "project_context.get" in READ_ONLY_TOOL_NAMES
    assert "task.get" in READ_ONLY_TOOL_NAMES
    assert "task.list_recent" in READ_ONLY_TOOL_NAMES
    assert "marketing_brief.get" in READ_ONLY_TOOL_NAMES
    assert "content_asset.list" in READ_ONLY_TOOL_NAMES


@pytest.mark.asyncio
async def test_executor_denied_real_tool_returns_permission_envelope() -> None:
    registry = ToolRegistry()
    registry.register(
        MEMORY_SEARCH_TOOL.model_copy(update={"allowed_agent_types": [AgentType.RESEARCHER]}),
    )
    executor = SafeNoOpToolExecutor(registry)
    result = await executor.execute(
        ToolCall(id="call_perm", name="memory.search", arguments={"query": "x"}),
        _context(agent_type=AgentType.COPYWRITER),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert (
        result.metadata["permission_reason_code"]
        == ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED.value
    )
    assert result.metadata["reason"] == "tool_not_allowed"


@pytest.mark.asyncio
async def test_executor_audit_logs_permission_reason(db_session: AsyncSession) -> None:
    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    context = _context()
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(registry, audit_service=audit_service)
    await executor.execute(
        ToolCall(id="call_unsup", name="memory.search", arguments={"query": "x"}),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        context.owner_id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].reason == "tool_execution_disabled"
    assert logs[0].status == "failed"

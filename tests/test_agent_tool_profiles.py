"""Phase 2.19 — per-agent-type tool allowlist tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.schemas.contracts import AgentType
from app.tools.agent_tool_profiles import (
    DEFAULT_AGENT_TOOL_ALLOWLIST,
    get_agent_tool_allowlist,
    is_tool_in_agent_allowlist,
)
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.permissions import ToolAccessReasonCode
from app.tools.registry import (
    CONTENT_ASSET_GET_TOOL,
    CONTENT_ASSET_LIST_TOOL,
    MARKETING_BRIEF_GET_TOOL,
    MARKETING_BRIEF_LIST_TOOL,
    MARKETING_FUNNEL_GAP_ANALYSIS_TOOL,
    MARKETING_FUNNEL_GET_TOOL,
    MARKETING_FUNNEL_LIST_TOOL,
    MARKETING_FUNNEL_STEP_ASSETS_TOOL,
    MEMORY_SEARCH_TOOL,
    PROJECT_CONTEXT_GET_TOOL,
    TASK_GET_TOOL,
    TASK_LIST_RECENT_TOOL,
    ToolRegistry,
    get_tool_registry,
)
from app.tools.result_contracts import ToolExecutionErrorCode
from tests.researcher_tool_names import RESEARCHER_READ_ONLY_TOOL_NAMES as EXPECTED_REAL_TOOLS


def _context(agent_type: AgentType) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
    )


def test_default_allowlist_covers_all_agent_types() -> None:
    for agent_type in AgentType:
        assert agent_type in DEFAULT_AGENT_TOOL_ALLOWLIST
        assert len(get_agent_tool_allowlist(agent_type)) >= 3


def test_strategist_sees_expected_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.STRATEGIST)
    names = [tool.name for tool in tools]
    for expected in EXPECTED_REAL_TOOLS:
        assert expected in names
    assert "campaign_asset.list" in names
    assert "content_asset.get" in names
    assert "search_brief" in get_agent_tool_allowlist(AgentType.STRATEGIST)


def test_copywriter_does_not_see_task_list_recent() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.COPYWRITER)
    names = [tool.name for tool in tools]
    assert "task.list_recent" not in names
    assert names == [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_funnel.get",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "task.get",
    ]


def test_analyst_does_not_see_task_get() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.ANALYST)
    names = [tool.name for tool in tools]
    assert "task.get" not in names
    assert names == [
        "campaign_asset.list",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "task.list_recent",
    ]


def test_orchestrator_sees_all_read_only_registered_tools() -> None:
    registry = ToolRegistry()
    for tool in (
        MEMORY_SEARCH_TOOL,
        PROJECT_CONTEXT_GET_TOOL,
        TASK_GET_TOOL,
        TASK_LIST_RECENT_TOOL,
        MARKETING_BRIEF_GET_TOOL,
        MARKETING_BRIEF_LIST_TOOL,
        CONTENT_ASSET_GET_TOOL,
        CONTENT_ASSET_LIST_TOOL,
        MARKETING_FUNNEL_GET_TOOL,
        MARKETING_FUNNEL_LIST_TOOL,
        MARKETING_FUNNEL_STEP_ASSETS_TOOL,
        MARKETING_FUNNEL_GAP_ANALYSIS_TOOL,
    ):
        registry.register(tool)
    registry.register(
        ToolDefinition(
            name="search_brief",
            description="Search brief",
            parameters_schema={"type": "object", "properties": {}},
            enabled=True,
        ),
    )
    tools = registry.list_for_agent(AgentType.ORCHESTRATOR)
    names = [tool.name for tool in tools]
    assert "search_brief" in names
    assert set(EXPECTED_REAL_TOOLS).issubset(set(names))


def test_researcher_keeps_full_real_tool_set() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    names = {tool.name for tool in tools}
    assert set(EXPECTED_REAL_TOOLS).issubset(names)
    assert is_tool_in_agent_allowlist(AgentType.RESEARCHER, "task.list_recent")
    assert is_tool_in_agent_allowlist(AgentType.RESEARCHER, "task.get")


@pytest.mark.asyncio
async def test_forbidden_direct_call_returns_permission_denied() -> None:
    executor = SafeNoOpToolExecutor(get_tool_registry())
    result = await executor.execute(
        ToolCall(id="call_copy_list", name="task.list_recent", arguments={"limit": 5}),
        _context(agent_type=AgentType.COPYWRITER),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert (
        result.metadata["permission_reason_code"]
        == ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST.value
    )
    assert result.metadata["reason"] == "tool_not_allowed"


@pytest.mark.asyncio
async def test_analyst_forbidden_task_get_returns_permission_denied() -> None:
    executor = SafeNoOpToolExecutor(get_tool_registry())
    result = await executor.execute(
        ToolCall(
            id="call_analyst_get",
            name="task.get",
            arguments={"task_id": str(uuid4())},
        ),
        _context(agent_type=AgentType.ANALYST),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert (
        result.metadata["permission_reason_code"]
        == ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST.value
    )

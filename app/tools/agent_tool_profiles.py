"""Per-agent-type tool allowlists for LLM exposure and execution."""

from __future__ import annotations

from app.schemas.contracts import AgentType
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CONTENT_ASSET_GET_TOOL_NAME,
    CONTENT_ASSET_LIST_TOOL_NAME,
)
from app.tools.write_tool_settings import is_write_tool_visible_to_agent

_BASE_REAL_READ_ONLY_TOOL_NAMES = frozenset(
    {
        "memory.search",
        "project_context.get",
        "task.get",
        "task.list_recent",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "marketing_funnel.gap_analysis",
    },
)

_CONTENT_ASSET_READ_TOOLS = frozenset(
    {
        CONTENT_ASSET_GET_TOOL_NAME,
        CONTENT_ASSET_LIST_TOOL_NAME,
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
    },
)

_CONTENT_ASSET_LIST_ONLY_TOOLS = frozenset(
    {
        CONTENT_ASSET_LIST_TOOL_NAME,
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
    },
)

_FUNNEL_READ_TOOLS = frozenset(
    {
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "marketing_funnel.gap_analysis",
    },
)

_COPYWRITER_FUNNEL_READ_TOOLS = frozenset(
    {
        "marketing_funnel.get",
        "marketing_funnel.step_assets",
    },
)

_MARKETING_READ_TOOLS = frozenset(
    {
        "marketing_brief.get",
        "marketing_brief.list",
    },
) | _CONTENT_ASSET_READ_TOOLS

_CAMPAIGN_READ_TOOLS = frozenset(
    {
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "publication_calendar.list",
    },
)

_CAMPAIGN_READ_TOOLS_NO_OVERVIEW = frozenset(
    {
        "marketing_campaign.get",
        "marketing_campaign.list",
        "publication_calendar.list",
    },
)

_MARKETING_BRIEF_READ_TOOLS = frozenset(
    {
        "marketing_brief.get",
        "marketing_brief.list",
    },
)

# Registered no-op stubs (not real executors) — still exposable per agent profile.
NO_OP_STUB_TOOL_NAMES = frozenset({"search_brief"})


def _with_no_op_stubs(names: frozenset[str]) -> frozenset[str]:
    return names | NO_OP_STUB_TOOL_NAMES


_STRATEGIST_TOOLS = _with_no_op_stubs(
    _BASE_REAL_READ_ONLY_TOOL_NAMES | _CONTENT_ASSET_READ_TOOLS | _CAMPAIGN_READ_TOOLS,
)

_COPYWRITER_TOOLS = _with_no_op_stubs(
    frozenset(
        {
            "project_context.get",
            "memory.search",
            "task.get",
        },
    )
    | _MARKETING_BRIEF_READ_TOOLS
    | _CONTENT_ASSET_READ_TOOLS
    | _CAMPAIGN_READ_TOOLS_NO_OVERVIEW
    | _COPYWRITER_FUNNEL_READ_TOOLS,
)

_ANALYST_TOOLS = _with_no_op_stubs(
    frozenset(
        {
            "project_context.get",
            "memory.search",
            "task.list_recent",
        },
    )
    | _MARKETING_BRIEF_READ_TOOLS
    | _CONTENT_ASSET_LIST_ONLY_TOOLS
    | _CAMPAIGN_READ_TOOLS
    | _FUNNEL_READ_TOOLS,
)

_CONTENT_PLANNER_TOOLS = _with_no_op_stubs(
    frozenset(
        {
            "project_context.get",
            "memory.search",
            "task.get",
        },
    )
    | _MARKETING_BRIEF_READ_TOOLS
    | _CONTENT_ASSET_READ_TOOLS
    | _CAMPAIGN_READ_TOOLS
    | _FUNNEL_READ_TOOLS,
)

_CRITIC_TOOLS = _with_no_op_stubs(
    frozenset(
        {
            "project_context.get",
            "memory.search",
            "task.get",
        },
    )
    | _MARKETING_BRIEF_READ_TOOLS
    | _CONTENT_ASSET_READ_TOOLS
    | _FUNNEL_READ_TOOLS,
)

_ORCHESTRATOR_TOOLS = (
    _with_no_op_stubs(
        _BASE_REAL_READ_ONLY_TOOL_NAMES | _CONTENT_ASSET_READ_TOOLS | _CAMPAIGN_READ_TOOLS,
    )
    | NO_OP_STUB_TOOL_NAMES
)

_GENERAL_TOOLS: frozenset[str] = frozenset()
_PROGRAMMER_TOOLS: frozenset[str] = frozenset()
_MEDIA_TOOLS: frozenset[str] = frozenset()

DEFAULT_AGENT_TOOL_ALLOWLIST: dict[AgentType, frozenset[str]] = {
    AgentType.GENERAL: _GENERAL_TOOLS,
    AgentType.PROGRAMMER: _PROGRAMMER_TOOLS,
    AgentType.MEDIA: _MEDIA_TOOLS,
    AgentType.STRATEGIST: _STRATEGIST_TOOLS,
    AgentType.RESEARCHER: _with_no_op_stubs(_BASE_REAL_READ_ONLY_TOOL_NAMES),
    AgentType.COPYWRITER: _COPYWRITER_TOOLS,
    AgentType.CONTENT_PLANNER: _CONTENT_PLANNER_TOOLS,
    AgentType.CRITIC: _CRITIC_TOOLS,
    AgentType.ANALYST: _ANALYST_TOOLS,
    AgentType.ORCHESTRATOR: _ORCHESTRATOR_TOOLS,
}


def get_agent_tool_allowlist(agent_type: AgentType) -> frozenset[str]:
    base = DEFAULT_AGENT_TOOL_ALLOWLIST[agent_type]
    extra: set[str] = set()
    if is_write_tool_visible_to_agent(agent_type, CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME):
        extra.add(CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME)
    if is_write_tool_visible_to_agent(agent_type, CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME):
        extra.add(CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME)
    if is_write_tool_visible_to_agent(agent_type, CONTENT_ASSET_CREATE_REVISION_TOOL_NAME):
        extra.add(CONTENT_ASSET_CREATE_REVISION_TOOL_NAME)
    if extra:
        return base | frozenset(extra)
    return base


def is_tool_in_agent_allowlist(agent_type: AgentType, tool_name: str) -> bool:
    return tool_name in get_agent_tool_allowlist(agent_type)

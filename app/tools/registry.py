"""Tool registry — allow-list definitions only, no execution."""

from __future__ import annotations

from app.schemas.contracts import AgentType
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.contracts import ToolDefinition, ToolName
from app.tools.errors import ToolDisabledError, ToolNotAllowedForAgentError, ToolNotFoundError
from app.tools.funnel_tools import (
    MARKETING_FUNNEL_GAP_ANALYSIS_PARAMETERS_SCHEMA,
    MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
    MARKETING_FUNNEL_GET_PARAMETERS_SCHEMA,
    MARKETING_FUNNEL_GET_TOOL_NAME,
    MARKETING_FUNNEL_LIST_PARAMETERS_SCHEMA,
    MARKETING_FUNNEL_LIST_TOOL_NAME,
    MARKETING_FUNNEL_STEP_ASSETS_PARAMETERS_SCHEMA,
    MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
)
from app.tools.marketing_tools import (
    CAMPAIGN_ASSET_LIST_PARAMETERS_SCHEMA,
    CAMPAIGN_PLAN_DRAFT_CREATE_PARAMETERS_SCHEMA,
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_PARAMETERS_SCHEMA,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    CONTENT_ASSET_CREATE_DRAFT_PARAMETERS_SCHEMA,
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_PARAMETERS_SCHEMA,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CONTENT_ASSET_GET_PARAMETERS_SCHEMA,
    CONTENT_ASSET_GET_TOOL_NAME,
    CONTENT_ASSET_LIST_PARAMETERS_SCHEMA,
    CONTENT_ASSET_LIST_TOOL_NAME,
    MARKETING_BRIEF_GET_PARAMETERS_SCHEMA,
    MARKETING_BRIEF_GET_TOOL_NAME,
    MARKETING_BRIEF_LIST_PARAMETERS_SCHEMA,
    MARKETING_BRIEF_LIST_TOOL_NAME,
    MARKETING_CAMPAIGN_GET_PARAMETERS_SCHEMA,
    MARKETING_CAMPAIGN_GET_TOOL_NAME,
    MARKETING_CAMPAIGN_LIST_PARAMETERS_SCHEMA,
    MARKETING_CAMPAIGN_LIST_TOOL_NAME,
    MARKETING_CAMPAIGN_OVERVIEW_PARAMETERS_SCHEMA,
    MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
    MARKETING_CAMPAIGN_WORKFLOW_PARAMETERS_SCHEMA,
    MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
    PUBLICATION_CALENDAR_LIST_PARAMETERS_SCHEMA,
    PUBLICATION_CALENDAR_LIST_TOOL_NAME,
)
from app.tools.permissions import (
    ToolAccessReasonCode,
    evaluate_tool_access,
    filter_tools_for_agent_from_registry,
)
from app.tools.project_context import (
    PROJECT_CONTEXT_GET_PARAMETERS_SCHEMA,
    PROJECT_CONTEXT_GET_TOOL_NAME,
)
from app.tools.review_queue_tools import (
    REVIEW_QUEUE_LIST_PARAMETERS_SCHEMA,
    REVIEW_QUEUE_LIST_TOOL_NAME,
)
from app.tools.task_tools import (
    TASK_GET_PARAMETERS_SCHEMA,
    TASK_GET_TOOL_NAME,
    TASK_LIST_RECENT_PARAMETERS_SCHEMA,
    TASK_LIST_RECENT_TOOL_NAME,
)

DEMO_DISABLED_TOOL = ToolDefinition(
    name="_demo_disabled",
    description="Placeholder tool for Phase 2.8 skeleton — disabled, never executed.",
    parameters_schema={"type": "object", "properties": {}},
    enabled=False,
    metadata={"phase": "2.8-skeleton"},
)

MEMORY_SEARCH_TOOL = ToolDefinition(
    name="memory.search",
    description="Search project memory by text query (read-only).",
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "agent_id": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

PROJECT_CONTEXT_GET_TOOL = ToolDefinition(
    name=PROJECT_CONTEXT_GET_TOOL_NAME,
    description="Read compact sanitized context for the current project.",
    parameters_schema=PROJECT_CONTEXT_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

TASK_GET_TOOL = ToolDefinition(
    name=TASK_GET_TOOL_NAME,
    description="Read a single task in the current project (read-only).",
    parameters_schema=TASK_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

TASK_LIST_RECENT_TOOL = ToolDefinition(
    name=TASK_LIST_RECENT_TOOL_NAME,
    description="List recent tasks in the current project (read-only).",
    parameters_schema=TASK_LIST_RECENT_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_BRIEF_GET_TOOL = ToolDefinition(
    name=MARKETING_BRIEF_GET_TOOL_NAME,
    description="Read a marketing brief in the current project (read-only).",
    parameters_schema=MARKETING_BRIEF_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_BRIEF_LIST_TOOL = ToolDefinition(
    name=MARKETING_BRIEF_LIST_TOOL_NAME,
    description="List marketing briefs in the current project (read-only).",
    parameters_schema=MARKETING_BRIEF_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

CONTENT_ASSET_GET_TOOL = ToolDefinition(
    name=CONTENT_ASSET_GET_TOOL_NAME,
    description="Read a content asset in the current project (read-only).",
    parameters_schema=CONTENT_ASSET_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

CONTENT_ASSET_LIST_TOOL = ToolDefinition(
    name=CONTENT_ASSET_LIST_TOOL_NAME,
    description="List content assets in the current project (read-only).",
    parameters_schema=CONTENT_ASSET_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

CAMPAIGN_ASSET_LIST_TOOL = ToolDefinition(
    name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
    description="List content assets for a single campaign (read-only).",
    parameters_schema=CAMPAIGN_ASSET_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

CONTENT_ASSET_CREATE_DRAFT_TOOL = ToolDefinition(
    name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    description="Create a draft content asset in the current project (write; draft status only).",
    parameters_schema=CONTENT_ASSET_CREATE_DRAFT_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "write", "execution_mode": "write"},
)

CONTENT_ASSET_CREATE_REVISION_TOOL = ToolDefinition(
    name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    description=(
        "Create a new draft version or revision from a draft/approved content asset "
        "(write; no approve/schedule/publish)."
    ),
    parameters_schema=CONTENT_ASSET_CREATE_REVISION_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "write", "execution_mode": "write"},
)

CAMPAIGN_PLAN_DRAFT_CREATE_TOOL = ToolDefinition(
    name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    description=(
        "Create a campaign plan draft (write; planning artifact only, no assets or jobs)."
    ),
    parameters_schema=CAMPAIGN_PLAN_DRAFT_CREATE_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "write", "execution_mode": "write"},
)

CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL = ToolDefinition(
    name=CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    description=(
        "Generate draft content assets from a campaign plan draft "
        "(write; draft assets only, no approve/schedule/publish)."
    ),
    parameters_schema=CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "write", "execution_mode": "write"},
)

MARKETING_CAMPAIGN_GET_TOOL = ToolDefinition(
    name=MARKETING_CAMPAIGN_GET_TOOL_NAME,
    description="Read a marketing campaign in the current project (read-only).",
    parameters_schema=MARKETING_CAMPAIGN_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_CAMPAIGN_LIST_TOOL = ToolDefinition(
    name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
    description="List marketing campaigns in the current project (read-only).",
    parameters_schema=MARKETING_CAMPAIGN_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_CAMPAIGN_OVERVIEW_TOOL = ToolDefinition(
    name=MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
    description="Read aggregated overview for a marketing campaign (read-only).",
    parameters_schema=MARKETING_CAMPAIGN_OVERVIEW_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_CAMPAIGN_WORKFLOW_TOOL = ToolDefinition(
    name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
    description=(
        "Read computed campaign execution workflow state and next recommended action (read-only)."
    ),
    parameters_schema=MARKETING_CAMPAIGN_WORKFLOW_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

REVIEW_QUEUE_LIST_TOOL = ToolDefinition(
    name=REVIEW_QUEUE_LIST_TOOL_NAME,
    description="List content assets awaiting human approval in the current project (read-only).",
    parameters_schema=REVIEW_QUEUE_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

PUBLICATION_CALENDAR_LIST_TOOL = ToolDefinition(
    name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
    description="List scheduled/queued/running publication jobs (read-only).",
    parameters_schema=PUBLICATION_CALENDAR_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_FUNNEL_GET_TOOL = ToolDefinition(
    name=MARKETING_FUNNEL_GET_TOOL_NAME,
    description="Read a marketing funnel and optional steps in the current project (read-only).",
    parameters_schema=MARKETING_FUNNEL_GET_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_FUNNEL_LIST_TOOL = ToolDefinition(
    name=MARKETING_FUNNEL_LIST_TOOL_NAME,
    description="List marketing funnels in the current project (read-only).",
    parameters_schema=MARKETING_FUNNEL_LIST_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_FUNNEL_STEP_ASSETS_TOOL = ToolDefinition(
    name=MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
    description="List content assets linked to a funnel step (read-only).",
    parameters_schema=MARKETING_FUNNEL_STEP_ASSETS_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)

MARKETING_FUNNEL_GAP_ANALYSIS_TOOL = ToolDefinition(
    name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
    description=(
        "Heuristic funnel gap analysis: missing journey steps and steps without assets (read-only)."
    ),
    parameters_schema=MARKETING_FUNNEL_GAP_ANALYSIS_PARAMETERS_SCHEMA,
    enabled=True,
    metadata={"access_mode": "read_only", "execution_mode": "read_only"},
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[ToolName, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, name: ToolName) -> ToolDefinition:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(
                f"Tool not found: {name}",
                tool_name=name,
                original_error_type="ToolNotFound",
            )
        return tool

    def list_registered(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def list_for_agent(self, agent_type: AgentType) -> list[ToolDefinition]:
        return filter_tools_for_agent_from_registry(agent_type, self)

    def validate_tool_allowed(self, name: ToolName, agent_type: AgentType) -> ToolDefinition:
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=name,
            registry=self,
        )
        if decision.allowed and decision.tool is not None:
            return decision.tool

        if decision.reason_code == ToolAccessReasonCode.TOOL_NOT_FOUND:
            raise ToolNotFoundError(
                decision.message,
                tool_name=name,
                original_error_type="ToolNotFound",
            )
        if decision.reason_code == ToolAccessReasonCode.TOOL_DISABLED:
            raise ToolDisabledError(
                decision.message,
                tool_name=name,
                original_error_type="ToolDisabled",
            )
        raise ToolNotAllowedForAgentError(
            decision.message,
            tool_name=name,
            original_error_type="ToolNotAllowedForAgent",
        )


def _build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(DEMO_DISABLED_TOOL)
    registry.register(MEMORY_SEARCH_TOOL)
    registry.register(PROJECT_CONTEXT_GET_TOOL)
    registry.register(TASK_GET_TOOL)
    registry.register(TASK_LIST_RECENT_TOOL)
    registry.register(MARKETING_BRIEF_GET_TOOL)
    registry.register(MARKETING_BRIEF_LIST_TOOL)
    registry.register(CONTENT_ASSET_GET_TOOL)
    registry.register(CONTENT_ASSET_LIST_TOOL)
    registry.register(CAMPAIGN_ASSET_LIST_TOOL)
    registry.register(MARKETING_CAMPAIGN_GET_TOOL)
    registry.register(MARKETING_CAMPAIGN_LIST_TOOL)
    registry.register(MARKETING_CAMPAIGN_OVERVIEW_TOOL)
    registry.register(MARKETING_CAMPAIGN_WORKFLOW_TOOL)
    registry.register(REVIEW_QUEUE_LIST_TOOL)
    registry.register(PUBLICATION_CALENDAR_LIST_TOOL)
    registry.register(CONTENT_ASSET_CREATE_DRAFT_TOOL)
    registry.register(CONTENT_ASSET_CREATE_REVISION_TOOL)
    registry.register(CAMPAIGN_PLAN_DRAFT_CREATE_TOOL)
    registry.register(CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL)
    registry.register(MARKETING_FUNNEL_GET_TOOL)
    registry.register(MARKETING_FUNNEL_LIST_TOOL)
    registry.register(MARKETING_FUNNEL_STEP_ASSETS_TOOL)
    registry.register(MARKETING_FUNNEL_GAP_ANALYSIS_TOOL)
    return registry


_default_registry = _build_default_registry()


def get_tool_registry() -> ToolRegistry:
    return _default_registry

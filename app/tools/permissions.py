"""Centralized tool permission matrix and access decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from app.schemas.contracts import AgentType
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.contracts import ToolDefinition, ToolExecutionContext
from app.tools.errors import ToolNotAllowedForAgentError, ToolNotFoundError
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
)
from app.tools.write_tool_settings import (
    LEGACY_WRITE_TOOL_NAMES,
    agent_write_tools_enabled,
    campaign_plan_draft_create_enabled,
    campaign_plan_draft_generate_assets_enabled,
    content_asset_create_draft_enabled,
    content_asset_create_revision_enabled,
    is_agent_type_allowed_for_campaign_plan_draft_create,
    is_agent_type_allowed_for_campaign_plan_draft_generate_assets,
    is_agent_type_allowed_for_create_draft,
    is_agent_type_allowed_for_create_revision,
)

if TYPE_CHECKING:
    from app.tools.registry import ToolRegistry

READ_ONLY_TOOL_NAMES = frozenset(
    {
        "memory.search",
        "project_context.get",
        "task.get",
        "task.list_recent",
        "marketing_brief.get",
        "marketing_brief.list",
        "content_asset.get",
        "content_asset.list",
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "publication_calendar.list",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "marketing_funnel.gap_analysis",
        "search_brief",
    },
)

REAL_READ_ONLY_EXECUTABLE_TOOLS = frozenset(
    {
        "memory.search",
        "project_context.get",
        "task.get",
        "task.list_recent",
        "marketing_brief.get",
        "marketing_brief.list",
        "content_asset.get",
        "content_asset.list",
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "publication_calendar.list",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "marketing_funnel.gap_analysis",
    },
)

WRITE_TOOL_NAMES = frozenset(
    {
        "memory.write",
        "task.create",
        "agent.update",
        CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
        CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
        CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
        CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    },
)

REAL_WRITE_EXECUTABLE_TOOLS = frozenset(
    {
        CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
        CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
        CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
        CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    },
)


class ToolExecutionMode(StrEnum):
    DISABLED = "disabled"
    NO_OP = "no_op"
    READ_ONLY = "read_only"
    WRITE = "write"


class ToolAccessReasonCode(StrEnum):
    ALLOWED = "allowed"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_DISABLED = "tool_disabled"
    TOOLS_DISABLED_FOR_AGENT = "tools_disabled_for_agent"
    TOOL_DENIED_BY_POLICY = "tool_denied_by_policy"
    TOOL_NOT_IN_ALLOWLIST = "tool_not_in_allowlist"
    WRITE_TOOL_NOT_ALLOWED = "write_tool_not_allowed"
    AGENT_TYPE_NOT_ALLOWED = "agent_type_not_allowed"
    EXECUTION_MODE_NOT_ALLOWED = "execution_mode_not_allowed"
    PROJECT_OWNERSHIP_INVALID = "project_ownership_invalid"
    UNSUPPORTED_TOOL = "unsupported_tool"
    WRITE_TOOLS_DISABLED = "write_tools_disabled"
    WRITE_TOOL_DISABLED = "write_tool_disabled"
    TOOL_NOT_ALLOWED_FOR_AGENT_TYPE = "tool_not_allowed_for_agent_type"


# Stable audit / metadata reason strings (legacy-compatible).
AUDIT_REASON_BY_CODE: dict[ToolAccessReasonCode, str] = {
    ToolAccessReasonCode.ALLOWED: "allowed",
    ToolAccessReasonCode.TOOL_NOT_FOUND: "tool_not_found",
    ToolAccessReasonCode.TOOL_DISABLED: "tool_disabled",
    ToolAccessReasonCode.TOOLS_DISABLED_FOR_AGENT: "tool_not_allowed",
    ToolAccessReasonCode.TOOL_DENIED_BY_POLICY: "tool_not_allowed",
    ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST: "tool_not_allowed",
    ToolAccessReasonCode.WRITE_TOOL_NOT_ALLOWED: "tool_not_allowed",
    ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED: "tool_not_allowed",
    ToolAccessReasonCode.EXECUTION_MODE_NOT_ALLOWED: "tool_not_allowed",
    ToolAccessReasonCode.PROJECT_OWNERSHIP_INVALID: "tool_not_allowed",
    ToolAccessReasonCode.UNSUPPORTED_TOOL: "tool_execution_disabled",
    ToolAccessReasonCode.WRITE_TOOLS_DISABLED: "write_tool_disabled",
    ToolAccessReasonCode.WRITE_TOOL_DISABLED: "write_tool_disabled",
    ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE: "tool_not_allowed_for_agent_type",
}


@dataclass(frozen=True)
class ToolAccessDecision:
    allowed: bool
    reason_code: ToolAccessReasonCode
    message: str
    execution_mode: ToolExecutionMode
    tool_name: str
    tool: ToolDefinition | None = None
    result_status: Literal["succeeded", "failed", "skipped"] = "skipped"

    @property
    def audit_reason(self) -> str:
        return AUDIT_REASON_BY_CODE[self.reason_code]

    @property
    def use_envelope(self) -> bool:
        if self.allowed:
            return False
        if self.tool_name in {
            CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
        }:
            return self.reason_code not in {ToolAccessReasonCode.TOOL_DISABLED}
        if not is_real_read_only_executable(self.tool_name):
            return False
        return self.reason_code not in {ToolAccessReasonCode.TOOL_DISABLED}


class ToolPermissionPolicy:
    __slots__ = ("agent_type", "allowed_tools", "denied_tools", "execution_mode")

    def __init__(
        self,
        *,
        agent_type: AgentType,
        allowed_tools: set[str],
        denied_tools: set[str],
        execution_mode: ToolExecutionMode,
    ) -> None:
        self.agent_type = agent_type
        self.allowed_tools = allowed_tools
        self.denied_tools = denied_tools
        self.execution_mode = execution_mode


def _base_policy(agent_type: AgentType) -> ToolPermissionPolicy:
    return ToolPermissionPolicy(
        agent_type=agent_type,
        allowed_tools=set(),
        denied_tools=set(LEGACY_WRITE_TOOL_NAMES),
        execution_mode=ToolExecutionMode.NO_OP,
    )


DEFAULT_TOOL_PERMISSION_MATRIX: dict[AgentType, ToolPermissionPolicy] = {
    AgentType.GENERAL: _base_policy(AgentType.GENERAL),
    AgentType.PROGRAMMER: _base_policy(AgentType.PROGRAMMER),
    AgentType.MEDIA: _base_policy(AgentType.MEDIA),
    AgentType.STRATEGIST: _base_policy(AgentType.STRATEGIST),
    AgentType.RESEARCHER: _base_policy(AgentType.RESEARCHER),
    AgentType.COPYWRITER: _base_policy(AgentType.COPYWRITER),
    AgentType.CONTENT_PLANNER: _base_policy(AgentType.CONTENT_PLANNER),
    AgentType.CRITIC: _base_policy(AgentType.CRITIC),
    AgentType.ANALYST: _base_policy(AgentType.ANALYST),
    AgentType.ORCHESTRATOR: _base_policy(AgentType.ORCHESTRATOR),
}


def get_tool_permission_policy(agent_type: AgentType) -> ToolPermissionPolicy:
    base = DEFAULT_TOOL_PERMISSION_MATRIX[agent_type]
    return ToolPermissionPolicy(
        agent_type=agent_type,
        allowed_tools=set(get_agent_tool_allowlist(agent_type)),
        denied_tools=base.denied_tools,
        execution_mode=base.execution_mode,
    )


def is_real_read_only_executable(tool_name: str) -> bool:
    return tool_name in REAL_READ_ONLY_EXECUTABLE_TOOLS


def _uses_envelope_on_deny(tool_name: str) -> bool:
    if tool_name in REAL_WRITE_EXECUTABLE_TOOLS:
        return True
    return is_real_read_only_executable(tool_name)


def get_tool_access_mode(tool: ToolDefinition) -> ToolExecutionMode:
    raw_mode = tool.metadata.get("access_mode") or tool.metadata.get("execution_mode")
    if raw_mode in {ToolExecutionMode.WRITE, ToolExecutionMode.WRITE.value, "write"}:
        return ToolExecutionMode.WRITE
    if tool.name in WRITE_TOOL_NAMES:
        return ToolExecutionMode.WRITE
    return ToolExecutionMode.READ_ONLY


def _validate_project_ownership(
    context: ToolExecutionContext | None,
    *,
    tool_name: str,
) -> ToolAccessDecision | None:
    if context is None:
        return None
    if context.owner_id is None or context.project_id is None:
        return ToolAccessDecision(
            allowed=False,
            reason_code=ToolAccessReasonCode.PROJECT_OWNERSHIP_INVALID,
            message="Project ownership context is invalid",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            result_status="failed",
        )
    return None


def _validate_run_context(
    context: ToolExecutionContext | None,
    *,
    tool_name: str,
) -> ToolAccessDecision | None:
    if context is None:
        return None
    required = {
        "agent_id": context.agent_id,
        "agent_run_id": context.agent_run_id,
    }
    for _field_name, value in required.items():
        if value is None:
            return ToolAccessDecision(
                allowed=False,
                reason_code=ToolAccessReasonCode.PROJECT_OWNERSHIP_INVALID,
                message="Agent run context is invalid",
                execution_mode=ToolExecutionMode.NO_OP,
                tool_name=tool_name,
                result_status="failed",
            )
    return None


def _evaluate_content_asset_create_draft_access(
    *,
    agent_type: AgentType,
    tool: ToolDefinition,
    context: ToolExecutionContext | None,
    policy: ToolPermissionPolicy,
) -> ToolAccessDecision:
    tool_name = CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME

    if not agent_write_tools_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOLS_DISABLED,
            message="Agent write tools are disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not content_asset_create_draft_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOL_DISABLED,
            message="content_asset.create_draft is disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not is_agent_type_allowed_for_create_draft(agent_type):
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE,
            message=(
                f"Tool {tool_name} is not allowed for agent type {agent_type.value}"
            ),
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    run_decision = _validate_run_context(context, tool_name=tool_name)
    if run_decision is not None:
        return run_decision

    if tool_name in policy.denied_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
            message=f"Tool {tool_name} is denied for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if policy.allowed_tools and tool_name not in policy.allowed_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST,
            message=f"Tool {tool_name} is not allowed for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    return _allow(tool, execution_mode=ToolExecutionMode.WRITE)


def _evaluate_content_asset_create_revision_access(
    *,
    agent_type: AgentType,
    tool: ToolDefinition,
    context: ToolExecutionContext | None,
    policy: ToolPermissionPolicy,
) -> ToolAccessDecision:
    tool_name = CONTENT_ASSET_CREATE_REVISION_TOOL_NAME

    if not agent_write_tools_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOLS_DISABLED,
            message="Agent write tools are disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not content_asset_create_revision_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOL_DISABLED,
            message="content_asset.create_revision is disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not is_agent_type_allowed_for_create_revision(agent_type):
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE,
            message=(
                f"Tool {tool_name} is not allowed for agent type {agent_type.value}"
            ),
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    run_decision = _validate_run_context(context, tool_name=tool_name)
    if run_decision is not None:
        return run_decision

    if tool_name in policy.denied_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
            message=f"Tool {tool_name} is denied for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if policy.allowed_tools and tool_name not in policy.allowed_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST,
            message=f"Tool {tool_name} is not allowed for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    return _allow(tool, execution_mode=ToolExecutionMode.WRITE)


def _evaluate_campaign_plan_draft_create_access(
    *,
    agent_type: AgentType,
    tool: ToolDefinition,
    context: ToolExecutionContext | None,
    policy: ToolPermissionPolicy,
) -> ToolAccessDecision:
    tool_name = CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME

    if not agent_write_tools_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOLS_DISABLED,
            message="Agent write tools are disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not campaign_plan_draft_create_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOL_DISABLED,
            message="campaign_plan_draft.create is disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not is_agent_type_allowed_for_campaign_plan_draft_create(agent_type):
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE,
            message=(
                f"Tool {tool_name} is not allowed for agent type {agent_type.value}"
            ),
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    run_decision = _validate_run_context(context, tool_name=tool_name)
    if run_decision is not None:
        return run_decision

    if tool_name in policy.denied_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
            message=f"Tool {tool_name} is denied for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if policy.allowed_tools and tool_name not in policy.allowed_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST,
            message=f"Tool {tool_name} is not allowed for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    return _allow(tool, execution_mode=ToolExecutionMode.WRITE)


def _evaluate_campaign_plan_draft_generate_assets_access(
    *,
    agent_type: AgentType,
    tool: ToolDefinition,
    context: ToolExecutionContext | None,
    policy: ToolPermissionPolicy,
) -> ToolAccessDecision:
    tool_name = CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME

    if not agent_write_tools_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOLS_DISABLED,
            message="Agent write tools are disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not campaign_plan_draft_generate_assets_enabled():
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOL_DISABLED,
            message="campaign_plan_draft.generate_assets is disabled",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    if not is_agent_type_allowed_for_campaign_plan_draft_generate_assets(agent_type):
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE,
            message=(
                f"Tool {tool_name} is not allowed for agent type {agent_type.value}"
            ),
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    run_decision = _validate_run_context(context, tool_name=tool_name)
    if run_decision is not None:
        return run_decision

    if tool_name in policy.denied_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
            message=f"Tool {tool_name} is denied for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.WRITE,
            tool_name=tool_name,
            tool=tool,
        )

    # Chat-only exposure via list_tools_for_agent_chat; skip global allowlist gate.
    return _allow(tool, execution_mode=ToolExecutionMode.WRITE)


def _deny(
    *,
    reason_code: ToolAccessReasonCode,
    message: str,
    execution_mode: ToolExecutionMode,
    tool_name: str,
    tool: ToolDefinition | None = None,
) -> ToolAccessDecision:
    result_status: Literal["succeeded", "failed", "skipped"] = "skipped"
    if _uses_envelope_on_deny(tool_name):
        result_status = (
            "skipped"
            if reason_code == ToolAccessReasonCode.TOOL_DISABLED
            else "failed"
        )
    elif reason_code == ToolAccessReasonCode.TOOL_NOT_FOUND:
        result_status = "failed"

    return ToolAccessDecision(
        allowed=False,
        reason_code=reason_code,
        message=message,
        execution_mode=execution_mode,
        tool_name=tool_name,
        tool=tool,
        result_status=result_status,
    )


def _allow(
    tool: ToolDefinition,
    *,
    execution_mode: ToolExecutionMode,
) -> ToolAccessDecision:
    return ToolAccessDecision(
        allowed=True,
        reason_code=ToolAccessReasonCode.ALLOWED,
        message="Tool access allowed",
        execution_mode=execution_mode,
        tool_name=tool.name,
        tool=tool,
        result_status="succeeded",
    )


def evaluate_tool_access(
    *,
    agent_type: AgentType,
    tool_name: str,
    context: ToolExecutionContext | None = None,
    tool: ToolDefinition | None = None,
    registry: ToolRegistry | None = None,
) -> ToolAccessDecision:
    policy = get_tool_permission_policy(agent_type)

    if policy.execution_mode == ToolExecutionMode.DISABLED:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOLS_DISABLED_FOR_AGENT,
            message=f"Tools disabled for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
        )

    ownership_decision = _validate_project_ownership(context, tool_name=tool_name)
    if ownership_decision is not None:
        return ownership_decision

    resolved_tool = tool
    if resolved_tool is None and registry is not None:
        try:
            resolved_tool = registry.get(tool_name)
        except ToolNotFoundError:
            resolved_tool = None

    if resolved_tool is None:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_FOUND,
            message=f"Tool not found: {tool_name}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
        )

    if not resolved_tool.enabled:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DISABLED,
            message=f"Tool is disabled: {tool_name}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            tool=resolved_tool,
        )

    if (
        resolved_tool.allowed_agent_types is not None
        and agent_type not in resolved_tool.allowed_agent_types
    ):
        return _deny(
            reason_code=ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED,
            message=(
                f"Tool {tool_name} is not allowed for agent type {agent_type.value}"
            ),
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            tool=resolved_tool,
        )

    access_mode = get_tool_access_mode(resolved_tool)
    if access_mode == ToolExecutionMode.WRITE:
        if tool_name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME:
            return _evaluate_content_asset_create_draft_access(
                agent_type=agent_type,
                tool=resolved_tool,
                context=context,
                policy=policy,
            )
        if tool_name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME:
            return _evaluate_campaign_plan_draft_create_access(
                agent_type=agent_type,
                tool=resolved_tool,
                context=context,
                policy=policy,
            )
        if tool_name == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME:
            return _evaluate_campaign_plan_draft_generate_assets_access(
                agent_type=agent_type,
                tool=resolved_tool,
                context=context,
                policy=policy,
            )
        if tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME:
            return _evaluate_content_asset_create_revision_access(
                agent_type=agent_type,
                tool=resolved_tool,
                context=context,
                policy=policy,
            )
        return _deny(
            reason_code=ToolAccessReasonCode.WRITE_TOOL_NOT_ALLOWED,
            message=f"Write tool {tool_name} is not allowed for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            tool=resolved_tool,
        )

    if tool_name in policy.denied_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
            message=f"Tool {tool_name} is denied for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            tool=resolved_tool,
        )

    if policy.allowed_tools and tool_name not in policy.allowed_tools:
        return _deny(
            reason_code=ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST,
            message=f"Tool {tool_name} is not allowed for agent type {agent_type.value}",
            execution_mode=ToolExecutionMode.NO_OP,
            tool_name=tool_name,
            tool=resolved_tool,
        )

    tool_execution_mode = get_tool_access_mode(resolved_tool)
    if tool_execution_mode == ToolExecutionMode.READ_ONLY:
        return _allow(resolved_tool, execution_mode=ToolExecutionMode.READ_ONLY)

    return _allow(resolved_tool, execution_mode=ToolExecutionMode.NO_OP)


def assert_tool_allowed(
    agent_type: AgentType,
    tool_name: str,
    *,
    tool: ToolDefinition | None = None,
) -> None:
    decision = evaluate_tool_access(agent_type=agent_type, tool_name=tool_name, tool=tool)
    if decision.allowed:
        return

    original_by_code = {
        ToolAccessReasonCode.TOOLS_DISABLED_FOR_AGENT: "ToolsDisabledForAgent",
        ToolAccessReasonCode.TOOL_DENIED_BY_POLICY: "ToolDeniedByPolicy",
        ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST: "ToolNotInAllowList",
        ToolAccessReasonCode.WRITE_TOOL_NOT_ALLOWED: "WriteToolNotAllowed",
        ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED: "ToolNotAllowedForAgent",
        ToolAccessReasonCode.EXECUTION_MODE_NOT_ALLOWED: "ExecutionModeNotAllowed",
    }
    raise ToolNotAllowedForAgentError(
        decision.message,
        tool_name=tool_name,
        original_error_type=original_by_code.get(
            decision.reason_code,
            "ToolNotAllowedForAgent",
        ),
    )


def filter_tools_for_agent(
    agent_type: AgentType,
    tools: list[ToolDefinition],
) -> list[ToolDefinition]:
    policy = get_tool_permission_policy(agent_type)
    if policy.execution_mode == ToolExecutionMode.DISABLED:
        return []

    filtered: list[ToolDefinition] = []
    for registered_tool in tools:
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=registered_tool.name,
            tool=registered_tool,
        )
        if decision.allowed:
            filtered.append(registered_tool)

    return sorted(filtered, key=lambda item: item.name)


def filter_tools_for_agent_from_registry(
    agent_type: AgentType,
    registry: ToolRegistry,
) -> list[ToolDefinition]:
    """Return registry tools allowed for the given agent type (LLM + execution allow-list)."""
    return filter_tools_for_agent(agent_type, registry.list_registered())


def build_permission_policy_metadata(
    agent_type: AgentType,
    available_tools: list[ToolDefinition],
) -> dict[str, str | int]:
    policy = get_tool_permission_policy(agent_type)
    return {
        "agent_type": agent_type.value,
        "execution_mode": ToolExecutionMode.NO_OP.value,
        "policy_execution_mode": policy.execution_mode.value,
        "allowed_tool_count": len(available_tools),
    }

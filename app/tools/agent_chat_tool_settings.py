"""Agent chat tool allowlist (Phase AI.3–AI.7) — narrow profile, chat runs only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.schemas.contracts import AgentType
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CONTENT_ASSET_GET_TOOL_NAME,
    MARKETING_CAMPAIGN_GET_TOOL_NAME,
    MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
    MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
)
from app.tools.write_tool_settings import (
    CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES,
    campaign_plan_draft_create_enabled,
    campaign_plan_draft_generate_assets_enabled,
    content_asset_create_revision_enabled,
)

if TYPE_CHECKING:
    from app.tools.registry import ToolRegistry

AGENT_CHAT_READ_TOOL_NAMES = frozenset(
    {
        MARKETING_CAMPAIGN_GET_TOOL_NAME,
        MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
    },
)

AGENT_CHAT_PLAN_DRAFT_WRITE_TOOL_NAMES = frozenset(
    {
        CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    },
)

AGENT_CHAT_GENERATE_ASSETS_TOOL_NAMES = frozenset(
    {
        CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    },
)

AGENT_CHAT_REVISION_WRITE_TOOL_NAMES = frozenset(
    {
        CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    },
)

AGENT_CHAT_REVISION_READ_TOOL_NAMES = frozenset(
    {
        CONTENT_ASSET_GET_TOOL_NAME,
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
        MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
    },
)

AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.CONTENT_PLANNER,
        AgentType.ORCHESTRATOR,
    },
)

AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES = (
    AGENT_CHAT_READ_TOOL_NAMES | AGENT_CHAT_PLAN_DRAFT_WRITE_TOOL_NAMES
)

AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES = (
    AGENT_CHAT_READ_TOOL_NAMES | AGENT_CHAT_GENERATE_ASSETS_TOOL_NAMES
)

AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES = (
    AGENT_CHAT_READ_TOOL_NAMES
    | AGENT_CHAT_REVISION_READ_TOOL_NAMES
    | AGENT_CHAT_REVISION_WRITE_TOOL_NAMES
)

AGENT_CHAT_TOOL_NAMES = (
    AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES
    | AGENT_CHAT_GENERATE_ASSETS_TOOL_NAMES
    | AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES
)


def _agent_chat_base_enabled() -> bool:
    settings = get_settings()
    return (
        settings.agent_chat_tools_enabled
        and settings.agent_write_tools_enabled
        and settings.tools_provider_enabled
    )


def agent_chat_tools_enabled() -> bool:
    return _agent_chat_base_enabled() and campaign_plan_draft_create_enabled()


def agent_chat_plan_draft_tools_enabled() -> bool:
    return agent_chat_tools_enabled() and campaign_plan_draft_create_enabled()


def agent_chat_generate_assets_tools_enabled() -> bool:
    return _agent_chat_base_enabled() and campaign_plan_draft_generate_assets_enabled()


def agent_chat_revision_tools_enabled() -> bool:
    return _agent_chat_base_enabled() and content_asset_create_revision_enabled()


def agent_chat_any_write_profile_enabled() -> bool:
    return (
        agent_chat_plan_draft_tools_enabled()
        or agent_chat_generate_assets_tools_enabled()
        or agent_chat_revision_tools_enabled()
    )


def is_agent_type_allowed_agent_chat_plan_create(agent_type: AgentType) -> bool:
    return agent_type in CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_agent_chat_generate_assets(agent_type: AgentType) -> bool:
    return agent_type in CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_agent_chat_revision(agent_type: AgentType) -> bool:
    return agent_type in AGENT_CHAT_REVISION_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_agent_chat_tools(agent_type: AgentType) -> bool:
    return (
        (
            agent_chat_plan_draft_tools_enabled()
            and is_agent_type_allowed_agent_chat_plan_create(agent_type)
        )
        or (
            agent_chat_generate_assets_tools_enabled()
            and is_agent_type_allowed_agent_chat_generate_assets(agent_type)
        )
        or (
            agent_chat_revision_tools_enabled()
            and is_agent_type_allowed_agent_chat_revision(agent_type)
        )
    )


def list_tools_for_agent_chat(registry: ToolRegistry, agent_type: AgentType) -> list:
    if not _agent_chat_base_enabled():
        return []
    if not agent_chat_any_write_profile_enabled():
        return []
    if not is_agent_type_allowed_agent_chat_tools(agent_type):
        return []

    allowed_names: set[str] = set()
    if agent_chat_plan_draft_tools_enabled() and is_agent_type_allowed_agent_chat_plan_create(
        agent_type,
    ):
        allowed_names |= AGENT_CHAT_PLAN_CREATE_PROFILE_TOOL_NAMES
    if agent_chat_generate_assets_tools_enabled() and (
        is_agent_type_allowed_agent_chat_generate_assets(agent_type)
    ):
        allowed_names |= AGENT_CHAT_GENERATE_ASSETS_PROFILE_TOOL_NAMES
    if agent_chat_revision_tools_enabled() and is_agent_type_allowed_agent_chat_revision(
        agent_type,
    ):
        allowed_names |= AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES

    return [
        registry.get(name)
        for name in sorted(allowed_names)
    ]

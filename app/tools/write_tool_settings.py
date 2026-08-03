"""Agent write tool feature flags (Phase 4.2, 10.2)."""

from __future__ import annotations

from app.core.config import get_settings
from app.marketing.contracts import ContentAssetType
from app.schemas.contracts import AgentType
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
)

CREATE_DRAFT_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.CONTENT_PLANNER,
        AgentType.CRITIC,
        AgentType.RESEARCHER,
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
    },
)

CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    },
)

CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    },
)

CREATE_REVISION_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.CONTENT_PLANNER,
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CRITIC,
    },
)

CONTENT_ASSET_CREATE_DRAFT_TYPE_ENUM = [item.value for item in ContentAssetType]

LEGACY_WRITE_TOOL_NAMES = frozenset(
    {
        "memory.write",
        "task.create",
        "agent.update",
    },
)


def agent_write_tools_enabled() -> bool:
    return get_settings().agent_write_tools_enabled


def content_asset_create_draft_enabled() -> bool:
    settings = get_settings()
    return (
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_content_asset_create_draft_enabled
    )


def campaign_plan_draft_create_enabled() -> bool:
    settings = get_settings()
    return (
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_campaign_plan_draft_create_enabled
    )


def campaign_plan_draft_generate_assets_enabled() -> bool:
    settings = get_settings()
    return (
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_campaign_plan_draft_generate_assets_enabled
    )


def content_asset_create_revision_enabled() -> bool:
    settings = get_settings()
    return (
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_content_asset_revision_enabled
    )


def get_agent_write_tool_body_max_chars() -> int:
    return get_settings().agent_write_tool_body_max_chars


def is_agent_type_allowed_for_create_draft(agent_type: AgentType) -> bool:
    return agent_type in CREATE_DRAFT_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_for_campaign_plan_draft_create(agent_type: AgentType) -> bool:
    return agent_type in CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_for_campaign_plan_draft_generate_assets(agent_type: AgentType) -> bool:
    return agent_type in CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ALLOWED_AGENT_TYPES


def is_agent_type_allowed_for_create_revision(agent_type: AgentType) -> bool:
    return agent_type in CREATE_REVISION_ALLOWED_AGENT_TYPES


def is_real_write_executable(tool_name: str) -> bool:
    if tool_name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME:
        return content_asset_create_draft_enabled()
    if tool_name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME:
        return campaign_plan_draft_create_enabled()
    if tool_name == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME:
        return campaign_plan_draft_generate_assets_enabled()
    if tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME:
        return content_asset_create_revision_enabled()
    return False


def is_write_tool_visible_to_agent(agent_type: AgentType, tool_name: str) -> bool:
    if tool_name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME:
        return content_asset_create_draft_enabled() and is_agent_type_allowed_for_create_draft(
            agent_type,
        )
    if tool_name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME:
        return (
            campaign_plan_draft_create_enabled()
            and is_agent_type_allowed_for_campaign_plan_draft_create(agent_type)
        )
    if tool_name == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME:
        return (
            campaign_plan_draft_generate_assets_enabled()
            and is_agent_type_allowed_for_campaign_plan_draft_generate_assets(agent_type)
        )
    if tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME:
        return (
            content_asset_create_revision_enabled()
            and is_agent_type_allowed_for_create_revision(agent_type)
        )
    return False

"""Phase 12.0 — campaign/content asset read tool access rules."""

from __future__ import annotations

from app.schemas.contracts import AgentType

CONTENT_ASSET_GET_BODY_ALLOWED_AGENT_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.CONTENT_PLANNER,
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CRITIC,
    },
)

CAMPAIGN_ASSET_LIST_TOOL_NAME = "campaign_asset.list"


def is_agent_allowed_content_asset_get_body(agent_type: AgentType) -> bool:
    return agent_type in CONTENT_ASSET_GET_BODY_ALLOWED_AGENT_TYPES

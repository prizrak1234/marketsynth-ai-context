"""Marketer sub-agent registry (Phase AI.10) — metadata only, no execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.marketer.contracts import MarketerSubAgentType
from app.schemas.contracts import AgentType
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CONTENT_ASSET_GET_TOOL_NAME,
    CONTENT_ASSET_LIST_TOOL_NAME,
)

FORBIDDEN_PERSONA_TOOLS = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)


@dataclass(frozen=True)
class MarketerSubAgentProfile:
    subagent_type: MarketerSubAgentType
    name: str
    description: str
    responsibilities: tuple[str, ...]
    allowed_tools: frozenset[str]
    mapped_agent_type: AgentType


_REGISTRY: dict[MarketerSubAgentType, MarketerSubAgentProfile] = {
    MarketerSubAgentType.STRATEGIST: MarketerSubAgentProfile(
        subagent_type=MarketerSubAgentType.STRATEGIST,
        name="Strategist",
        description="Campaign planning, goals, and structured plan drafts.",
        responsibilities=(
            "Define campaign goals and messaging direction",
            "Shape plan draft structure and content_items",
            "Align tactics with workflow_state",
        ),
        allowed_tools=frozenset(
            {
                "marketing_campaign.get",
                "marketing_campaign.workflow",
                "marketing_brief.get",
                "marketing_brief.list",
                CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            },
        ),
        mapped_agent_type=AgentType.STRATEGIST,
    ),
    MarketerSubAgentType.COPYWRITER: MarketerSubAgentProfile(
        subagent_type=MarketerSubAgentType.COPYWRITER,
        name="Copywriter",
        description="Draft and approved-source content improvement.",
        responsibilities=(
            "Improve and rewrite content assets",
            "Adapt tone to campaign key_message",
            "Prepare drafts for human review",
        ),
        allowed_tools=frozenset(
            {
                CONTENT_ASSET_GET_TOOL_NAME,
                CAMPAIGN_ASSET_LIST_TOOL_NAME,
                CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
                "marketing_campaign.get",
            },
        ),
        mapped_agent_type=AgentType.COPYWRITER,
    ),
    MarketerSubAgentType.ANALYST: MarketerSubAgentProfile(
        subagent_type=MarketerSubAgentType.ANALYST,
        name="Analyst",
        description="Campaign workflow and review-queue analysis.",
        responsibilities=(
            "Analyze campaign workflow and asset counts",
            "Summarize review queue and calendar posture",
            "Recommend human next steps from facts",
        ),
        allowed_tools=frozenset(
            {
                "marketing_campaign.get",
                "marketing_campaign.overview",
                "marketing_campaign.workflow",
                "review_queue.list",
                "publication_calendar.list",
                CAMPAIGN_ASSET_LIST_TOOL_NAME,
                CONTENT_ASSET_LIST_TOOL_NAME,
            },
        ),
        mapped_agent_type=AgentType.ANALYST,
    ),
    MarketerSubAgentType.RESEARCHER: MarketerSubAgentProfile(
        subagent_type=MarketerSubAgentType.RESEARCHER,
        name="Researcher",
        description="Brief and audience background research.",
        responsibilities=(
            "Gather brief and project context",
            "Clarify audience and offer assumptions",
            "Support strategists with evidence-backed notes",
        ),
        allowed_tools=frozenset(
            {
                "marketing_brief.get",
                "marketing_brief.list",
                "project_context.get",
                "memory.search",
                "task.get",
            },
        ),
        mapped_agent_type=AgentType.RESEARCHER,
    ),
}


def list_subagents() -> list[MarketerSubAgentProfile]:
    return [_REGISTRY[key] for key in MarketerSubAgentType]


def get_subagent(subagent_type: MarketerSubAgentType) -> MarketerSubAgentProfile:
    return _REGISTRY[subagent_type]


def get_subagent_prompt(subagent_type: MarketerSubAgentType) -> str:
    from app.prompts.marketer_subagents import get_prompt_for_subagent

    return get_prompt_for_subagent(subagent_type)


def validate_subagent_tool_allowlist(profile: MarketerSubAgentProfile) -> None:
    forbidden = profile.allowed_tools & FORBIDDEN_PERSONA_TOOLS
    if forbidden:
        raise ValueError(f"Persona {profile.subagent_type} includes forbidden tools: {forbidden}")

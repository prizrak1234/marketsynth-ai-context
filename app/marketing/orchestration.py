"""Orchestrator specialist routing and child run payload conventions (Phase 5.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.contracts import AgentStatus, AgentType
from app.services.agents import AgentService
from app.tools.security import sanitize_tool_payload

_RESEARCHER_GOAL_MARKERS = (
    "research",
    "unknown",
    "investigate",
    "open question",
)
_STRATEGIST_GOAL_MARKERS = (
    "strategy",
    "strategic",
    "positioning",
    "position",
    "gap analysis",
    "funnel gap",
)
_PLANNER_GOAL_MARKERS = (
    "content plan",
    "plan content",
    "editorial",
    "content calendar",
    "production plan",
)
_COPYWRITER_GOAL_MARKERS = (
    "copy",
    "write email",
    "write ad",
    "draft email",
    "draft ad",
    "landing copy",
    "telegram post",
)
_CRITIC_GOAL_MARKERS = (
    "review",
    "critique",
    "quality check",
    "critic",
)


@dataclass(frozen=True)
class OrchestrationConfig:
    handoff_enabled: bool = True
    max_child_runs: int = 3
    default_inline_child_execution: bool = False


def parse_orchestration_config(agent_config: dict[str, Any] | None) -> OrchestrationConfig:
    if not isinstance(agent_config, dict):
        return OrchestrationConfig()
    raw = agent_config.get("orchestration")
    if not isinstance(raw, dict):
        return OrchestrationConfig()
    max_child_runs = raw.get("max_child_runs", 3)
    try:
        max_child_runs = max(1, int(max_child_runs))
    except (TypeError, ValueError):
        max_child_runs = 3
    return OrchestrationConfig(
        handoff_enabled=bool(raw.get("handoff_enabled", True)),
        max_child_runs=max_child_runs,
        default_inline_child_execution=bool(raw.get("default_inline_child_execution", False)),
    )


def _normalized_goal(payload: dict[str, Any]) -> str:
    goal = payload.get("goal")
    if goal is None:
        prompt = payload.get("prompt")
        if isinstance(prompt, str):
            return prompt.strip().lower()
        return ""
    return str(goal).strip().lower()


def resolve_specialist_agent_type(payload: dict[str, Any]) -> AgentType | None:
    """Pick a specialist agent type from orchestrator run scope (goal and IDs)."""
    research_topic = payload.get("research_topic")
    if research_topic is not None and str(research_topic).strip():
        return AgentType.RESEARCHER

    goal = _normalized_goal(payload)
    source_asset_id = payload.get("source_asset_id")

    if source_asset_id is not None and str(source_asset_id).strip():
        if any(marker in goal for marker in _CRITIC_GOAL_MARKERS):
            return AgentType.CRITIC
        if any(marker in goal for marker in _COPYWRITER_GOAL_MARKERS) or payload.get("step_id"):
            return AgentType.COPYWRITER

    if any(marker in goal for marker in _CRITIC_GOAL_MARKERS):
        return AgentType.CRITIC
    if any(marker in goal for marker in _RESEARCHER_GOAL_MARKERS):
        return AgentType.RESEARCHER
    if any(marker in goal for marker in _PLANNER_GOAL_MARKERS):
        return AgentType.CONTENT_PLANNER
    if any(marker in goal for marker in _COPYWRITER_GOAL_MARKERS):
        return AgentType.COPYWRITER
    if payload.get("step_id") or payload.get("asset_type"):
        return AgentType.COPYWRITER
    if any(marker in goal for marker in _STRATEGIST_GOAL_MARKERS):
        return AgentType.STRATEGIST
    if "plan" in goal:
        return AgentType.CONTENT_PLANNER
    if goal:
        return AgentType.STRATEGIST
    return None


def _copy_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_specialist_child_payload(
    target_agent_type: AgentType | str | None,
    parent_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build child input_payload fields per specialist conventions."""
    if isinstance(target_agent_type, str):
        try:
            agent_type = AgentType(target_agent_type.strip().lower())
        except ValueError:
            agent_type = None
    else:
        agent_type = target_agent_type

    fields: dict[str, Any] = {}
    goal = _copy_field(parent_payload, "goal")
    if goal:
        fields["goal"] = goal

    brief_id = _copy_field(parent_payload, "brief_id")
    funnel_id = _copy_field(parent_payload, "funnel_id")

    if agent_type == AgentType.RESEARCHER:
        if brief_id:
            fields["brief_id"] = brief_id
        if funnel_id:
            fields["funnel_id"] = funnel_id
        research_topic = _copy_field(parent_payload, "research_topic")
        if research_topic:
            fields["research_topic"] = research_topic
    elif agent_type == AgentType.STRATEGIST or agent_type == AgentType.CONTENT_PLANNER:
        if brief_id:
            fields["brief_id"] = brief_id
        if funnel_id:
            fields["funnel_id"] = funnel_id
    elif agent_type == AgentType.COPYWRITER:
        if brief_id:
            fields["brief_id"] = brief_id
        if funnel_id:
            fields["funnel_id"] = funnel_id
        for key in ("step_id", "source_asset_id", "asset_type"):
            value = _copy_field(parent_payload, key)
            if value:
                fields[key] = value
    elif agent_type == AgentType.CRITIC:
        source_asset_id = _copy_field(parent_payload, "source_asset_id")
        if source_asset_id:
            fields["source_asset_id"] = source_asset_id
        if brief_id:
            fields["brief_id"] = brief_id
        if funnel_id:
            fields["funnel_id"] = funnel_id

    sanitized = sanitize_tool_payload(fields)
    return sanitized if isinstance(sanitized, dict) else {}


async def resolve_project_agent_id_for_type(
    session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    agent_type: AgentType,
) -> UUID | None:
    agents = await AgentService(session).list_agents(
        owner_id,
        project_id=project_id,
        include_archived=False,
    )
    for row in agents:
        if row.type == agent_type and row.status != AgentStatus.ARCHIVED:
            return row.id
    return None


def parse_handoff_target_agent_type(raw: Any) -> AgentType | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return AgentType(raw.strip().lower())
    except ValueError:
        return None

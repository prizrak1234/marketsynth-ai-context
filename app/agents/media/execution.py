"""Media delegation execution (Phase AI.17) — single child run, no sub-agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.media.contracts import MediaOutputKind
from app.agents.media.prompts import VISUAL_BRIEF_TITLE
from app.core.exceptions import ExecutorError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.executors.agent_run_coordinator import AgentRunCoordinator
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService


def infer_visual_format(*, message: str) -> str:
    normalized = " ".join((message or "").lower().split())
    if "telegram" in normalized or "телеграм" in normalized:
        return "telegram_banner"
    if any(token in normalized for token in ("сторис", "stories", "reels", "shorts")):
        return "short_form_video"
    if any(token in normalized for token in ("видео", "video", "ролик")):
        return "video_concept"
    if any(token in normalized for token in ("логотип", "logo")):
        return "logo_concept"
    if any(token in normalized for token in ("обложка", "cover")):
        return "cover_art"
    return "general_visual"


def build_visual_brief(*, message: str, assistant_excerpt: str) -> dict[str, Any]:
    """In-memory visual brief (no persistence in AI.17)."""
    summary = (message or "").strip()[:500]
    excerpt = (assistant_excerpt or "").strip()[:2000]
    visual_format = infer_visual_format(message=message)
    return {
        "kind": MediaOutputKind.VISUAL_BRIEF.value,
        "title": VISUAL_BRIEF_TITLE,
        "persisted": False,
        "format": visual_format,
        "concept": summary or "Visual concept to be refined with the design team.",
        "composition": (
            "Headline zone, primary visual focal point, supporting elements, "
            "and clear CTA placement suitable for the target channel."
        ),
        "text_overlay": "Draft headline and subline placeholders aligned with campaign tone.",
        "style_notes": (
            "Consultation-only: color mood, typography direction, and reference style. "
            "No asset files generated."
        ),
        "shot_list": [
            "Hero frame / key visual",
            "Supporting detail or product highlight",
            "CTA closing frame",
        ],
        "assistant_excerpt": excerpt,
    }


def merge_media_output_payload(
    *,
    run: AgentRunTable,
    message: str,
) -> dict[str, Any]:
    output = dict(run.output_payload or {})
    llm_content = ""
    if isinstance(output.get("content"), str):
        llm_content = output["content"]
    elif isinstance(output.get("llm_content"), str):
        llm_content = output["llm_content"]
    output["media_mode"] = MediaOutputKind.CONSULTATION.value
    output["visual_brief"] = build_visual_brief(message=message, assistant_excerpt=llm_content)
    return output


@dataclass(frozen=True)
class MediaDelegationResult:
    final_run: AgentRunTable


async def resolve_project_media_agent_id(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
) -> UUID:
    agents = await AgentService(session).list_agents(owner_id, project_id=project_id)
    matching = [
        agent
        for agent in agents
        if agent.type == AgentType.MEDIA and agent.status != AgentStatus.ARCHIVED
    ]
    active = [agent for agent in matching if agent.status == AgentStatus.ACTIVE]
    pool = active or matching
    if not pool:
        raise NotFoundError("No media agent available in project")
    return pool[0].id


async def execute_media_delegation(
    session: AsyncSession,
    *,
    media_parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
    message: str,
) -> MediaDelegationResult:
    """
    Run a single Media child under General. No child runs, tools, or external execution.
    """
    agent_runs = AgentRunService(session)
    parent_agent = await agent_runs.get_executable_agent(media_parent_run.agent_id, owner_id)
    if parent_agent.type != AgentType.MEDIA:
        raise ExecutorError("Media delegation requires media agent")

    final_run, _engine = await AgentRunCoordinator(session).execute_run(
        media_parent_run.id,
        owner_id,
        request_engine="classic",
    )
    if final_run.status != AgentRunStatus.SUCCEEDED:
        raise ExecutorError("Media specialist temporarily unavailable")

    enriched = merge_media_output_payload(run=final_run, message=message)
    persisted = await agent_runs.patch_output_payload(
        owner_id,
        final_run.id,
        enriched,
    )
    if persisted is None:
        raise ExecutorError("Media run output could not be saved")

    return MediaDelegationResult(final_run=persisted)

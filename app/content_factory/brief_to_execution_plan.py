"""Map Content Factory brief fields to frozen MarketingExecutionPlan."""

from __future__ import annotations

from app.agents.marketer.marketing_specialist_registry import get_marketing_specialist
from app.core.security import sanitize_text
from app.schemas.contracts import (
    ContentFactoryBriefInput,
    MarketingExecutionMode,
    MarketingExecutionPlan,
    MarketingSpecialistTask,
    MarketingSpecialistType,
)

_PIPELINE_SPECIALISTS: tuple[MarketingSpecialistType, ...] = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.COPYWRITER,
)


def _build_goal(brief: ContentFactoryBriefInput) -> str:
    topic = sanitize_text(brief.topic).strip()
    goal = sanitize_text(brief.goal).strip()
    audience = sanitize_text(brief.audience).strip()
    return (
        f"Content campaign — topic: {topic}. Goal: {goal}. Audience: {audience}."
    )[:4096]


def brief_to_execution_plan(brief: ContentFactoryBriefInput) -> MarketingExecutionPlan:
    tasks: list[MarketingSpecialistTask] = []
    for specialist in _PIPELINE_SPECIALISTS:
        profile = get_marketing_specialist(specialist)
        tasks.append(
            MarketingSpecialistTask(
                specialist=specialist,
                objective=profile.default_objective,
                expected_output=profile.default_expected_output,
            ),
        )

    project_context = {
        "content_factory_brief": {
            "topic": sanitize_text(brief.topic).strip(),
            "goal": sanitize_text(brief.goal).strip(),
            "audience": sanitize_text(brief.audience).strip(),
            "channel": sanitize_text(brief.channel).strip(),
            "period": sanitize_text(brief.period).strip(),
            "frequency": sanitize_text(brief.frequency).strip(),
            "format": sanitize_text(brief.format).strip(),
            "tone_brand_constraints": sanitize_text(brief.tone_brand_constraints).strip(),
            "source_materials": sanitize_text(brief.source_materials).strip(),
        },
        "primary_channel": sanitize_text(brief.channel).strip(),
    }
    if brief.idempotency_key:
        project_context["content_factory_idempotency_key"] = sanitize_text(
            brief.idempotency_key,
        ).strip()[:128]

    return MarketingExecutionPlan(
        goal=_build_goal(brief),
        project_context=project_context,
        specialist_tasks=tasks,
        execution_mode=MarketingExecutionMode.PLANNING,
    )

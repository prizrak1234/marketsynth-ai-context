"""Marketing orchestrator planning mode (Phase AI.27) — plans only, no execution."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.marketing_specialist_registry import (
    get_marketing_specialist,
    list_frozen_pipeline_specialists,
)
from app.core.exceptions import ExecutorError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.schemas.contracts import (
    AgentRunStatus,
    AgentType,
    MarketingExecutionMode,
    MarketingExecutionPlan,
    MarketingSpecialistTask,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService


def _message_from_input_payload(input_payload: dict[str, Any]) -> str:
    prompt = input_payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    agent_chat = input_payload.get("agent_chat")
    if isinstance(agent_chat, dict):
        nested = agent_chat.get("prompt")
        if isinstance(nested, str):
            return nested
    return ""


_STRATEGY_MARKERS = (
    "контент-стратег",
    "контент стратег",
    "content strategy",
    "стратегия",
    "позиционирован",
    "запусти",
    "launch",
    "кампани",
    "campaign",
)

_RESEARCH_MARKERS = (
    "исслед",
    "аудитор",
    "research",
    "audience",
    "рынок",
    "market",
)

_CONTENT_PLAN_MARKERS = (
    "контент-план",
    "контент план",
    "content plan",
    "план контента",
    "календар",
    "calendar",
)

_COPY_MARKERS = (
    "перепиш",
    "текст",
    "пост",
    "copy",
    "rewrite",
    "improve",
)

_ANALYST_MARKERS = (
    "анализ",
    "проанализ",
    "analyze",
    "метрик",
    "performance",
    "review queue",
)

_PLANNING_OUTPUT_KEY = "marketing_execution_plan"


def extract_project_context_from_payload(input_payload: dict[str, Any]) -> dict[str, Any]:
    """Safe subset of run input for plan context — no secrets or tool logs."""
    context: dict[str, Any] = {}
    for key in ("project_id", "workflow_context", "scenario_context"):
        value = input_payload.get(key)
        if value is not None:
            context[key] = value
    agent_chat = input_payload.get("agent_chat")
    if isinstance(agent_chat, dict):
        for key in ("campaign_id", "workflow_state"):
            value = agent_chat.get(key)
            if value is not None:
                context[key] = value
    return context


def _normalized_message(message: str) -> str:
    return sanitize_text(message).strip().lower()


def _message_has_any(message: str, markers: tuple[str, ...]) -> bool:
    return any(marker in message for marker in markers)


def select_specialists_for_message(message: str) -> list[MarketingSpecialistType]:
    """Rule-based specialist selection for planning skeleton (no LLM)."""
    normalized = _normalized_message(message)
    if not normalized:
        return [MarketingSpecialistType.STRATEGIST, MarketingSpecialistType.CRITIC]

    selected: list[MarketingSpecialistType] = []

    if _message_has_any(normalized, _COPY_MARKERS) and not _message_has_any(
        normalized,
        _STRATEGY_MARKERS,
    ):
        selected.extend(
            [
                MarketingSpecialistType.COPYWRITER,
                MarketingSpecialistType.CRITIC,
            ],
        )
        return selected

    if _message_has_any(normalized, _STRATEGY_MARKERS) or _message_has_any(
        normalized,
        _CONTENT_PLAN_MARKERS,
    ):
        selected.extend(
            [
                MarketingSpecialistType.STRATEGIST,
                MarketingSpecialistType.RESEARCHER,
                MarketingSpecialistType.CONTENT_PLANNER,
                MarketingSpecialistType.COPYWRITER,
                MarketingSpecialistType.CRITIC,
            ],
        )
    else:
        selected.append(MarketingSpecialistType.STRATEGIST)

    if _message_has_any(normalized, _RESEARCH_MARKERS):
        if MarketingSpecialistType.RESEARCHER not in selected:
            selected.append(MarketingSpecialistType.RESEARCHER)

    if _message_has_any(normalized, _CONTENT_PLAN_MARKERS):
        if MarketingSpecialistType.CONTENT_PLANNER not in selected:
            selected.append(MarketingSpecialistType.CONTENT_PLANNER)

    if _message_has_any(normalized, _COPY_MARKERS):
        if MarketingSpecialistType.COPYWRITER not in selected:
            selected.append(MarketingSpecialistType.COPYWRITER)

    if _message_has_any(normalized, _ANALYST_MARKERS):
        selected.append(MarketingSpecialistType.ANALYST)

    if MarketingSpecialistType.CRITIC not in selected:
        selected.append(MarketingSpecialistType.CRITIC)

    seen: set[MarketingSpecialistType] = set()
    ordered: list[MarketingSpecialistType] = []
    for specialist in selected:
        if specialist not in seen:
            seen.add(specialist)
            ordered.append(specialist)
    return ordered


def _localize_objective(profile_objective: str, message: str) -> str:
    """Attach user goal hint when message mentions a vertical (e.g. dentistry)."""
    normalized = _normalized_message(message)
    vertical_match = re.search(
        r"(?:для|for)\s+([a-zа-яё0-9\s\-]{3,40})",
        normalized,
        flags=re.IGNORECASE,
    )
    if vertical_match:
        vertical = vertical_match.group(1).strip(" .,;")
        if vertical and len(vertical) >= 3:
            return f"{profile_objective} ({vertical})"
    return profile_objective


def build_marketing_execution_plan(
    *,
    message: str,
    project_context: dict[str, Any] | None = None,
) -> MarketingExecutionPlan:
    goal = sanitize_text(message).strip() or "Marketing request"
    specialists = select_specialists_for_message(goal)
    tasks: list[MarketingSpecialistTask] = []
    for specialist_type in specialists:
        profile = get_marketing_specialist(specialist_type)
        tasks.append(
            MarketingSpecialistTask(
                specialist=specialist_type,
                objective=_localize_objective(profile.default_objective, goal),
                expected_output=profile.default_expected_output,
            ),
        )
    return MarketingExecutionPlan(
        goal=goal,
        project_context=dict(project_context or {}),
        specialist_tasks=tasks,
        execution_mode=MarketingExecutionMode.PLANNING,
        created_at=utc_now(),
    )


def format_marketing_execution_plan_summary(plan: MarketingExecutionPlan) -> str:
    lines = [f"Goal: {plan.goal.strip()}", "", "Specialist tasks:"]
    for task in plan.specialist_tasks:
        lines.append(
            f"- {task.specialist.value}: {task.objective} → {task.expected_output}",
        )
    lines.append("")
    lines.append("Planning mode only — execution is not available in this phase.")
    return "\n".join(lines)


def marketing_plan_to_output_payload(plan: MarketingExecutionPlan) -> dict[str, Any]:
    summary = format_marketing_execution_plan_summary(plan)
    return {
        _PLANNING_OUTPUT_KEY: plan.model_dump(mode="json"),
        "content": summary,
    }


async def execute_marketer_orchestrator_planning(
    session: AsyncSession,
    *,
    orchestrator_parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
) -> "MarketerOrchestratorDelegationResult":
    """
    Complete orchestrator run with a MarketingExecutionPlan — no child runs or tools.
    """
    agent_runs = AgentRunService(session)
    parent_agent = await agent_runs.get_executable_agent(
        orchestrator_parent_run.agent_id,
        owner_id,
    )
    if parent_agent.type != AgentType.ORCHESTRATOR:
        raise ExecutorError("Marketer planning requires orchestrator agent")

    message = _message_from_input_payload(input_payload)
    project_context = extract_project_context_from_payload(input_payload)
    plan = build_marketing_execution_plan(
        message=message,
        project_context=project_context,
    )
    output_payload = marketing_plan_to_output_payload(plan)

    running = await agent_runs.mark_running(owner_id, orchestrator_parent_run.id)
    if running is None:
        raise ExecutorError("Orchestrator run not found")

    final_run = await agent_runs.mark_succeeded(
        owner_id,
        orchestrator_parent_run.id,
        output_payload,
    )
    if final_run is None or final_run.status != AgentRunStatus.SUCCEEDED:
        raise ExecutorError("Failed to persist marketing execution plan")

    child_count = await agent_runs.count_children(orchestrator_parent_run.id, owner_id)
    if child_count != 0:
        raise ExecutorError("Planning mode must not create child runs")

    from app.agents.marketer.orchestrator_delegation import planning_mode_delegation_result

    return planning_mode_delegation_result(final_run)


def registry_specialist_type_values() -> list[str]:
    return [profile.specialist_type.value for profile in list_frozen_pipeline_specialists()]

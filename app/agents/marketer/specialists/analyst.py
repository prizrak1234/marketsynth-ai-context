"""Analyst specialist execution (Phase AI.36) — feasibility analysis only."""

from __future__ import annotations

import json
from typing import Any

from app.agents.marketer.specialists.base import (
    build_specialist_llm_input,
    build_specialist_llm_metadata,
    format_project_context_block,
    merge_structured_with_llm_meta,
    reject_tool_calls,
    resolve_project_llm_config,
    safe_summary_from_content,
    sanitize_execution_input,
    truncate_content,
)
from app.agents.marketer.specialists.researcher import (
    STRATEGIST_PRIOR_STRUCTURED_KEYS,
    RESEARCHER_PRIOR_STRUCTURED_KEYS,
    CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
    COPYWRITER_PRIOR_STRUCTURED_KEYS,
    CRITIC_PRIOR_STRUCTURED_KEYS,
)
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMMessage
from app.llm.registry import get_llm_adapter
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)

_ANALYST_SYSTEM_PROMPT = (
    "You are a marketing execution analyst for BotFazer. Assess feasibility and "
    "realism of the full specialist pipeline output.\n"
    "Use only provided plan context and prior specialist structured summaries.\n"
    "Do not request tools, publish, or change run status.\n"
    "Provide desk-level execution analysis with risks, resources, channel fit, "
    "funnel gaps, complexity, and KPI recommendations."
)

_ANALYST_TITLE = "Execution analysis"
_ANALYST_OUTPUT_TYPE = "analysis"

_PRIOR_KEYS_BY_SPECIALIST = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CONTENT_PLANNER: CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.COPYWRITER: COPYWRITER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CRITIC: CRITIC_PRIOR_STRUCTURED_KEYS,
}


def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    if not prior_outputs:
        return "No prior specialist outputs."
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        allowed = _PRIOR_KEYS_BY_SPECIALIST.get(item.specialist, ())
        safe_structured = {key: structured[key] for key in allowed if key in structured}
        blocks.append(
            json.dumps(
                {
                    "specialist": item.specialist.value,
                    "title": item.title,
                    "output_type": item.output_type,
                    "safe_summary": item.safe_summary,
                    "structured_data": safe_structured,
                    "content_excerpt": item.content_excerpt,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return "\n\n".join(blocks)


def _build_user_message(data: MarketingSpecialistExecutionInput) -> str:
    return (
        f"Plan goal:\n{data.plan_goal}\n\n"
        f"Task objective:\n{data.objective}\n\n"
        f"Expected output:\n{data.expected_output}\n\n"
        f"Project context:\n{format_project_context_block(data.project_context)}\n\n"
        f"Prior specialist outputs (full pipeline):\n"
        f"{_format_prior_outputs_block(data.prior_outputs)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_ANALYST_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _prior_present(
    prior_outputs: list[MarketingSpecialistPriorOutput],
    specialist: MarketingSpecialistType,
) -> bool:
    return any(item.specialist == specialist for item in prior_outputs)


def validate_analyst_prior_outputs(
    prior_outputs: list[MarketingSpecialistPriorOutput],
) -> None:
    required = (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
    )
    for specialist in required:
        if not _prior_present(prior_outputs, specialist):
            raise ExecutorError(f"Analyst execution requires prior {specialist.value} context")


def _critic_recommendation(data: MarketingSpecialistExecutionInput) -> str:
    critic = next(
        (p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.CRITIC),
        None,
    )
    if critic and critic.structured_data:
        return str(critic.structured_data.get("approval_recommendation", "revise"))
    return "revise"


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    goal = data.plan_goal.strip() or "the approved marketing plan"
    recommendation = _critic_recommendation(data)
    complexity = "medium" if recommendation == "revise" else "low"
    return {
        "risks": [
            "Desk-only research may miss live competitive pricing moves",
            "Channel capacity not validated against real publishing calendar",
        ],
        "resource_requirements": [
            "Human editor for copy polish after critic revise pass",
            "One channel owner per primary distribution surface",
        ],
        "channel_fit": [
            "Email and social drafts align with planner channel recommendations",
            "Proof assets may be needed before paid amplification",
        ],
        "funnel_gaps": [
            "Confirm consideration-stage nurture between awareness and conversion items",
        ],
        "execution_complexity": complexity,
        "kpi_recommendations": [
            f"Track leading indicator: engaged sessions on top-of-funnel items for {goal[:80]}",
            "Measure CTA click-through after revisions land",
            "Review critic recommendation outcome before scaling spend",
        ],
    }


def _mock_content_body(data: MarketingSpecialistExecutionInput, structured: dict[str, Any]) -> str:
    goal = data.plan_goal.strip() or "the approved plan"
    lines = [
        f"Execution analysis for {goal} (feasibility desk review).",
        f"\n## Complexity\n{structured['execution_complexity']}",
        "\n## Risks",
    ]
    lines.extend(f"- {item}" for item in structured["risks"])
    lines.append("\n## Resource requirements")
    lines.extend(f"- {item}" for item in structured["resource_requirements"])
    lines.append("\n## Channel fit")
    lines.extend(f"- {item}" for item in structured["channel_fit"])
    lines.append("\n## Funnel gaps")
    lines.extend(f"- {item}" for item in structured["funnel_gaps"])
    lines.append("\n## KPI recommendations")
    lines.extend(f"- {item}" for item in structured["kpi_recommendations"])
    return truncate_content("\n".join(lines))


def _build_mock_output(
    data: MarketingSpecialistExecutionInput,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    structured = merge_structured_with_llm_meta(
        _mock_structured_data(data),
        provider=provider,
        model=model,
    )
    content = _mock_content_body(data, structured)
    return MarketingSpecialistExecutionOutput(
        title=_ANALYST_TITLE,
        output_type=_ANALYST_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            f"Complexity: {structured['execution_complexity']}",
            prefix="Analysis (mock):",
        ),
    )


def _fallback_structured() -> dict[str, Any]:
    return {
        "risks": ["Execution risks require human validation against live constraints"],
        "resource_requirements": ["Assign owners per channel before launch"],
        "channel_fit": ["Validate channel mix against audience research"],
        "funnel_gaps": ["Map missing nurture steps between funnel stages"],
        "execution_complexity": "medium",
        "kpi_recommendations": ["Define baseline metrics before first publish wave"],
    }


def _build_from_llm_content(
    content: str,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    body = truncate_content(content)
    structured = merge_structured_with_llm_meta(
        _fallback_structured(),
        provider=provider,
        model=model,
    )
    return MarketingSpecialistExecutionOutput(
        title=_ANALYST_TITLE,
        output_type=_ANALYST_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            f"Complexity: {structured['execution_complexity']}",
            prefix="Analysis:",
        ),
    )


async def execute_analyst_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Feasibility analysis from full pipeline — no tools or run auto-complete."""
    sanitized = sanitize_execution_input(data)
    validate_analyst_prior_outputs(sanitized.prior_outputs)

    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.ANALYST,
    )
    llm_input = build_specialist_llm_input(
        provider=provider,
        model=model,
        messages=_build_messages(sanitized),
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=metadata,
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Analyst LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        provider=provider,
        model=model or output.model or "unknown",
    )

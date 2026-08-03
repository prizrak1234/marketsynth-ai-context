"""Critic specialist execution (Phase AI.35) — quality review only, no auto actions."""

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

_CRITIC_SYSTEM_PROMPT = (
    "You are a marketing quality critic for BotFazer. Review strategist direction, "
    "research, content plan, and draft copy.\n"
    "Provide a desk critique only — do not approve, publish, or modify assets. "
    "Do not request tools.\n"
    "Respond in markdown with clear strengths, gaps, and actionable improvements. "
    "End with a single recommendation: approve, revise, or reject."
)

_CRITIC_TITLE = "Content critique"
_CRITIC_OUTPUT_TYPE = "critique"

_APPROVAL_VALUES = frozenset({"approve", "revise", "reject"})

_PRIOR_KEYS_BY_SPECIALIST = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CONTENT_PLANNER: CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.COPYWRITER: COPYWRITER_PRIOR_STRUCTURED_KEYS,
}

_STRUCTURED_KEYS = (
    "strengths",
    "weaknesses",
    "inconsistencies",
    "missing_information",
    "improvement_actions",
    "approval_recommendation",
)


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
        f"Prior strategist, researcher, content planner, and copywriter outputs:\n"
        f"{_format_prior_outputs_block(data.prior_outputs)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_CRITIC_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _prior_present(
    prior_outputs: list[MarketingSpecialistPriorOutput],
    specialist: MarketingSpecialistType,
) -> bool:
    return any(item.specialist == specialist for item in prior_outputs)


def validate_critic_prior_outputs(
    prior_outputs: list[MarketingSpecialistPriorOutput],
) -> None:
    if not _prior_present(prior_outputs, MarketingSpecialistType.STRATEGIST):
        raise ExecutorError("Critic execution requires prior strategist context")
    if not _prior_present(prior_outputs, MarketingSpecialistType.RESEARCHER):
        raise ExecutorError("Critic execution requires prior researcher context")
    if not _prior_present(prior_outputs, MarketingSpecialistType.CONTENT_PLANNER):
        raise ExecutorError("Critic execution requires prior content planner context")
    if not _prior_present(prior_outputs, MarketingSpecialistType.COPYWRITER):
        raise ExecutorError("Critic execution requires prior copywriter context")


def _normalize_approval(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _APPROVAL_VALUES:
        return normalized
    return "revise"


def _copy_item_count(data: MarketingSpecialistExecutionInput) -> int:
    copywriter = next(
        (p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.COPYWRITER),
        None,
    )
    if not copywriter or not copywriter.structured_data:
        return 0
    items = copywriter.structured_data.get("content_items")
    return len(items) if isinstance(items, list) else 0


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    item_count = _copy_item_count(data) or 1
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "strengths": [
            f"Draft copy covers {item_count} planned content item(s) aligned with the plan goal",
            "Messaging stays within strategist positioning and researcher audience framing",
        ],
        "weaknesses": [
            "Some CTAs are generic placeholders pending human polish",
            "Channel-specific proof points could be sharper before publish",
        ],
        "inconsistencies": [
            "Verify funnel_stage labels match the content plan sequence for each item",
        ],
        "missing_information": [
            "Live customer quotes or case metrics not available in desk-research mode",
            "Final brand voice guidelines beyond project context snapshot",
        ],
        "improvement_actions": [
            "Tighten hooks per channel using researcher pains and desires",
            "Add one proof element per high-intent funnel stage item",
            "Human editor to confirm CTA URLs and compliance before any asset conversion",
        ],
        "approval_recommendation": "revise",
    }


def _mock_content_body(data: MarketingSpecialistExecutionInput, structured: dict[str, Any]) -> str:
    goal = data.plan_goal.strip() or "the approved plan"
    recommendation = structured["approval_recommendation"]
    lines = [
        f"Quality critique for {goal} (desk review — no automatic approval).",
        f"\n## Recommendation\n{recommendation.upper()} — human must decide before publishing.",
        "\n## Strengths",
    ]
    lines.extend(f"- {item}" for item in structured["strengths"])
    lines.append("\n## Weaknesses")
    lines.extend(f"- {item}" for item in structured["weaknesses"])
    lines.append("\n## Inconsistencies")
    lines.extend(f"- {item}" for item in structured["inconsistencies"])
    lines.append("\n## Missing information")
    lines.extend(f"- {item}" for item in structured["missing_information"])
    lines.append("\n## Improvement actions")
    lines.extend(f"- {item}" for item in structured["improvement_actions"])
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
        title=_CRITIC_TITLE,
        output_type=_CRITIC_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            f"Recommendation: {structured['approval_recommendation']}",
            prefix="Critique (mock):",
        ),
    )


def _fallback_structured_from_content(content: str) -> dict[str, Any]:
    seed = content.strip()[:200] or "Draft copy review"
    return {
        "strengths": ["Clear structure in the submitted draft package"],
        "weaknesses": ["Requires human pass for channel-specific polish"],
        "inconsistencies": [],
        "missing_information": ["Additional proof points may be needed pre-publish"],
        "improvement_actions": [
            "Apply editor revisions per weakness notes",
            f"Re-check alignment with plan goal: {seed[:80]}",
        ],
        "approval_recommendation": "revise",
    }


def _build_from_llm_content(
    content: str,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    body = truncate_content(content)
    base = _fallback_structured_from_content(body)
    lowered = body.lower()
    for word in ("approve", "revise", "reject"):
        if word in lowered:
            base["approval_recommendation"] = _normalize_approval(word)
            break
    structured = merge_structured_with_llm_meta(base, provider=provider, model=model)
    return MarketingSpecialistExecutionOutput(
        title=_CRITIC_TITLE,
        output_type=_CRITIC_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            f"Recommendation: {structured['approval_recommendation']}",
            prefix="Critique:",
        ),
    )


async def execute_critic_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Quality review from full prior pipeline — no tools, assets, or auto approve/reject."""
    sanitized = sanitize_execution_input(data)
    validate_critic_prior_outputs(sanitized.prior_outputs)

    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.CRITIC,
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
        raise ExecutorError("Critic LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        provider=provider,
        model=model or output.model or "unknown",
    )

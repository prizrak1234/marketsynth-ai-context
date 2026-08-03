"""Funnel Architect specialist execution (Phase AI.112) — funnel design only."""

from __future__ import annotations

import json
from typing import Any

from app.agents.marketer.specialists.base import (
    build_specialist_llm_input,
    build_specialist_llm_metadata,
    format_project_context_block,
    merge_structured_with_llm_meta,
    parse_markdown_sections,
    reject_tool_calls,
    resolve_project_llm_config,
    safe_summary_from_content,
    sanitize_execution_input,
    truncate_content,
)
from app.agents.marketer.specialists.offer_strategist import (
    OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
)
from app.agents.marketer.specialists.researcher import (
    RESEARCHER_PRIOR_STRUCTURED_KEYS,
    STRATEGIST_PRIOR_STRUCTURED_KEYS,
    prior_output_from_row,
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

_SYSTEM_PROMPT = (
    "You are a funnel architect for BotFazer. Map stages from awareness to retention.\n"
    "Use strategist, researcher, and offer strategist outputs — no copy or assets.\n"
    "Do not request tools. Respond in markdown with:\n"
    "## Summary\n"
    "## Funnel stages\n"
    "## Entry points\n"
    "## Lead capture\n"
    "## Nurture sequence\n"
    "## Conversion events\n"
    "## Retention actions\n"
)

_TITLE = "Funnel design"
_OUTPUT_TYPE = "funnel_design"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.OFFER_STRATEGIST,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
}

FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS = (
    "funnel_stages",
    "entry_points",
    "lead_capture",
    "nurture_sequence",
    "conversion_events",
    "retention_actions",
)


def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        allowed = _PRIOR_KEYS.get(item.specialist, ())
        safe_structured = {key: structured[key] for key in allowed if key in structured}
        blocks.append(
            json.dumps(
                {
                    "specialist": item.specialist.value,
                    "structured_data": safe_structured,
                    "safe_summary": item.safe_summary,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return "\n\n".join(blocks) or "No prior specialist outputs."


def _assert_required_prior_outputs(prior_outputs: list[MarketingSpecialistPriorOutput]) -> None:
    present = {item.specialist for item in prior_outputs}
    if not all(required in present for required in _REQUIRED_PRIOR):
        raise ExecutorError(
            "Funnel Architect execution requires strategist, researcher, and offer context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "funnel_stages": ["Awareness", "Consideration", "Conversion", "Retention"],
        "entry_points": ["Organic social", "Referral", "Lead magnet landing"],
        "lead_capture": "Email opt-in with offer-aligned lead magnet hook",
        "nurture_sequence": [
            "Welcome + deliver lead magnet",
            "Proof and objection handling",
            "Offer invitation with risk reversal",
        ],
        "conversion_events": ["Discovery call booked", "Checkout completed"],
        "retention_actions": ["Onboarding check-in", "Upsell to premium tier"],
    }


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
    content = truncate_content(
        "## Summary\n"
        f"Funnel for {data.plan_goal[:200]}\n\n"
        "## Funnel stages\n"
        + "\n".join(f"- {stage}" for stage in structured["funnel_stages"]),
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            ", ".join(structured["funnel_stages"][:3]),
            prefix="Funnel design (mock):",
        ),
    )


def _parse_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Funnel stages",
            "Entry points",
            "Lead capture",
            "Nurture sequence",
            "Conversion events",
            "Retention actions",
        ),
    )
    return {
        "funnel_stages": _list_from_section(
            sections.get("funnel_stages") or "Awareness\nConsideration\nConversion",
        ),
        "entry_points": _list_from_section(
            sections.get("entry_points") or "Primary channel entry",
        ),
        "lead_capture": sections.get("lead_capture") or "Lead capture mechanism",
        "nurture_sequence": _list_from_section(
            sections.get("nurture_sequence") or "Nurture step one",
        ),
        "conversion_events": _list_from_section(
            sections.get("conversion_events") or "Primary conversion event",
        ),
        "retention_actions": _list_from_section(
            sections.get("retention_actions") or "Retention follow-up",
        ),
    }


async def execute_funnel_architect_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    sanitized = sanitize_execution_input(data)
    _assert_required_prior_outputs(sanitized.prior_outputs)

    provider, model, temperature, max_tokens = resolve_project_llm_config()
    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    user_message = (
        f"Plan goal:\n{sanitized.plan_goal}\n\n"
        f"Task objective:\n{sanitized.objective}\n\n"
        f"Expected output:\n{sanitized.expected_output}\n\n"
        f"Project context:\n{format_project_context_block(sanitized.project_context)}\n\n"
        f"Prior outputs:\n{_format_prior_outputs_block(sanitized.prior_outputs)}"
    )
    llm_input = build_specialist_llm_input(
        provider=provider,
        model=model,
        messages=[
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_message),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=build_specialist_llm_metadata(
            execution_run_id=str(sanitized.execution_run_id),
            task_index=sanitized.task_index,
            specialist=MarketingSpecialistType.FUNNEL_ARCHITECT,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Funnel Architect LLM returned empty content")
    body = truncate_content(output.content)
    structured = merge_structured_with_llm_meta(
        _parse_content(body),
        provider=provider,
        model=model or output.model or "unknown",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            ", ".join(structured["funnel_stages"][:3]),
            prefix="Funnel design:",
        ),
    )


__all__ = [
    "FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS",
    "execute_funnel_architect_specialist",
    "prior_output_from_row",
]

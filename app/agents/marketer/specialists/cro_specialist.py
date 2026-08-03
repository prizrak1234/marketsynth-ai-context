"""CRO Specialist execution (Phase AI.116) — recommendations only, no A/B runs."""

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
from app.agents.marketer.specialists.funnel_architect import FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS
from app.agents.marketer.specialists.offer_strategist import OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS
from app.agents.marketer.specialists.researcher import prior_output_from_row
from app.agents.marketer.specialists.sales_copywriter import SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS
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

_TITLE = "CRO recommendations"
_OUTPUT_TYPE = "cro_recommendations"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.FUNNEL_ARCHITECT,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.FUNNEL_ARCHITECT: FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.SALES_COPYWRITER: SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS,
}

CRO_PRIOR_STRUCTURED_KEYS = (
    "conversion_bottlenecks",
    "landing_page_recommendations",
    "cta_improvements",
    "trust_elements",
    "form_optimization",
    "test_hypotheses",
    "priority_actions",
)


def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        allowed = _PRIOR_KEYS.get(item.specialist, ())
        safe_structured = {key: structured[key] for key in allowed if key in structured}
        blocks.append(json.dumps({"specialist": item.specialist.value, "structured_data": safe_structured}))
    return "\n\n".join(blocks) or "No prior specialist outputs."


def _assert_required_prior_outputs(prior_outputs: list[MarketingSpecialistPriorOutput]) -> None:
    present = {item.specialist for item in prior_outputs}
    if not all(required in present for required in _REQUIRED_PRIOR):
        raise ExecutorError(
            "CRO Specialist requires prior offer, funnel, and sales copy context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "conversion_bottlenecks": [
            "Weak trust signals above the fold",
            "CTA not aligned with top objection",
        ],
        "landing_page_recommendations": [
            "Move proof block before pricing",
            "Clarify offer outcome in hero subhead",
        ],
        "cta_improvements": ["Use outcome-led CTA copy", "Add risk reversal near primary CTA"],
        "trust_elements": ["Case study snippet", "Guarantee badge", "Founder credibility line"],
        "form_optimization": ["Reduce fields to email + goal", "Add progress indicator on multi-step"],
        "test_hypotheses": [
            "Hero headline variant A vs B on opt-in rate",
            "CTA color + copy combo on click-through",
        ],
        "priority_actions": [
            "Fix hero clarity first",
            "Test primary CTA copy second",
            "Add trust row third",
        ],
    }


async def execute_cro_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    sanitized = sanitize_execution_input(data)
    _assert_required_prior_outputs(sanitized.prior_outputs)
    provider, model, temperature, max_tokens = resolve_project_llm_config()
    if provider == LLMProvider.MOCK:
        structured = merge_structured_with_llm_meta(
            _mock_structured_data(sanitized),
            provider=provider,
            model=model,
        )
        content = truncate_content(
            "## Summary\nCRO recommendations based on offer, funnel, and sales copy.\n",
        )
        return MarketingSpecialistExecutionOutput(
            title=_TITLE,
            output_type=_OUTPUT_TYPE,
            content=content,
            structured_data=structured,
            safe_summary=safe_summary_from_content(
                structured["priority_actions"][0],
                prefix="CRO (mock):",
            ),
        )

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
            LLMMessage(
                role="system",
                content=(
                    "You are a CRO specialist for BotFazer. Recommend conversion improvements only.\n"
                    "Do not request tools. Use markdown sections for bottlenecks, landing page, CTA, "
                    "trust, forms, test hypotheses, and priority actions."
                ),
            ),
            LLMMessage(role="user", content=user_message),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=build_specialist_llm_metadata(
            execution_run_id=str(sanitized.execution_run_id),
            task_index=sanitized.task_index,
            specialist=MarketingSpecialistType.CRO_SPECIALIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("CRO Specialist LLM returned empty content")
    body = truncate_content(output.content)
    sections = parse_markdown_sections(
        body,
        (
            "Conversion bottlenecks",
            "Landing page recommendations",
            "CTA improvements",
            "Trust elements",
            "Form optimization",
            "Test hypotheses",
            "Priority actions",
        ),
    )
    structured = merge_structured_with_llm_meta(
        {
            "conversion_bottlenecks": _list_from_section(
                sections.get("conversion_bottlenecks") or "Primary conversion bottleneck",
            ),
            "landing_page_recommendations": _list_from_section(
                sections.get("landing_page_recommendations") or "Landing page improvement",
            ),
            "cta_improvements": _list_from_section(
                sections.get("cta_improvements") or "CTA improvement",
            ),
            "trust_elements": _list_from_section(
                sections.get("trust_elements") or "Trust element to add",
            ),
            "form_optimization": _list_from_section(
                sections.get("form_optimization") or "Form optimization",
            ),
            "test_hypotheses": _list_from_section(
                sections.get("test_hypotheses") or "Test hypothesis",
            ),
            "priority_actions": _list_from_section(
                sections.get("priority_actions") or "Priority action",
            ),
        },
        provider=provider,
        model=model or output.model or "unknown",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured["priority_actions"][0]),
            prefix="CRO:",
        ),
    )


__all__ = ["CRO_PRIOR_STRUCTURED_KEYS", "execute_cro_specialist", "prior_output_from_row"]

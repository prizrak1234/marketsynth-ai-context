"""Ad Creative Strategist execution (Phase AI.118) — creative strategy only."""

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
from app.agents.marketer.specialists.offer_strategist import OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS
from app.agents.marketer.specialists.researcher import (
    RESEARCHER_PRIOR_STRUCTURED_KEYS,
    prior_output_from_row,
)
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

_TITLE = "Ad creative strategy"
_OUTPUT_TYPE = "ad_creative_strategy"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.SALES_COPYWRITER: SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS,
}

AD_CREATIVE_PRIOR_STRUCTURED_KEYS = (
    "creative_angles",
    "ad_hooks",
    "visual_concepts",
    "primary_text_variants",
    "headline_variants",
    "cta_variants",
    "testing_matrix",
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
            "Ad Creative Strategist requires prior offer, research, and sales copy context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "creative_angles": ["Outcome-first", "Problem-agitate", "Social proof lead"],
        "ad_hooks": ["Stop losing leads to unclear offers", "What if your funnel converted 2x?"],
        "visual_concepts": ["Split-screen before/after", "Founder talking head + captions"],
        "primary_text_variants": ["Short punchy primary", "Story-led primary with proof"],
        "headline_variants": ["Get [outcome] without [pain]", "The [mechanism] for [audience]"],
        "cta_variants": ["Book a call", "Get the checklist", "See pricing"],
        "testing_matrix": [
            "Hook A vs B on CTR",
            "Visual concept 1 vs 2 on CPC",
            "CTA copy on conversion rate",
        ],
    }


async def execute_ad_creative_strategist_specialist(
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
        content = truncate_content("## Summary\nAd creative strategy from offer and sales copy.\n")
        return MarketingSpecialistExecutionOutput(
            title=_TITLE,
            output_type=_OUTPUT_TYPE,
            content=content,
            structured_data=structured,
            safe_summary=safe_summary_from_content(
                structured["creative_angles"][0],
                prefix="Ad creative (mock):",
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
                content="You are an ad creative strategist for BotFazer. Strategy only — no media buying.",
            ),
            LLMMessage(role="user", content=user_message),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=build_specialist_llm_metadata(
            execution_run_id=str(sanitized.execution_run_id),
            task_index=sanitized.task_index,
            specialist=MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Ad Creative Strategist LLM returned empty content")
    body = truncate_content(output.content)
    sections = parse_markdown_sections(
        body,
        (
            "Creative angles",
            "Ad hooks",
            "Visual concepts",
            "Primary text variants",
            "Headline variants",
            "CTA variants",
            "Testing matrix",
        ),
    )
    structured = merge_structured_with_llm_meta(
        {
            "creative_angles": _list_from_section(sections.get("creative_angles") or "Outcome angle"),
            "ad_hooks": _list_from_section(sections.get("ad_hooks") or "Primary hook"),
            "visual_concepts": _list_from_section(sections.get("visual_concepts") or "Visual concept"),
            "primary_text_variants": _list_from_section(
                sections.get("primary_text_variants") or "Primary text variant",
            ),
            "headline_variants": _list_from_section(
                sections.get("headline_variants") or "Headline variant",
            ),
            "cta_variants": _list_from_section(sections.get("cta_variants") or "CTA variant"),
            "testing_matrix": _list_from_section(sections.get("testing_matrix") or "Test matrix row"),
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
            str(structured["creative_angles"][0]),
            prefix="Ad creative:",
        ),
    )


__all__ = [
    "AD_CREATIVE_PRIOR_STRUCTURED_KEYS",
    "execute_ad_creative_strategist_specialist",
    "prior_output_from_row",
]

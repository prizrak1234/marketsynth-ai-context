"""Offer Strategist specialist execution (Phase AI.111) — offer design only."""

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

_OFFER_STRATEGIST_SYSTEM_PROMPT = (
    "You are an offer strategist for BotFazer. Design the core offer only.\n"
    "Use strategist direction and researcher insights — no funnel, copy, or assets.\n"
    "Do not request tools. Respond in markdown with:\n"
    "## Summary\n"
    "## Core offer\n"
    "## Value proposition\n"
    "## Unique mechanism\n"
    "## Offer variants\n"
    "## Pricing hypotheses\n"
    "## Risk reversal\n"
    "## Positioning statement\n"
)

_TITLE = "Offer strategy"
_OUTPUT_TYPE = "offer_strategy"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
}

OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS = (
    "core_offer",
    "value_proposition",
    "unique_mechanism",
    "offer_variants",
    "pricing_hypotheses",
    "risk_reversal",
    "positioning_statement",
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
                    "title": item.title,
                    "output_type": item.output_type,
                    "safe_summary": item.safe_summary,
                    "structured_data": safe_structured,
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
            "Offer Strategist execution requires prior strategist and researcher context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "core_offer": f"Structured offer package aligned with {goal[:180]}",
        "value_proposition": "Clear outcome promise backed by strategist positioning and research.",
        "unique_mechanism": "Differentiated delivery method that reduces perceived risk.",
        "offer_variants": [
            "Core entry offer for primary segment",
            "Premium bundle with added proof assets",
        ],
        "pricing_hypotheses": [
            "Value-anchored tier matching researcher objections",
            "Intro price to validate conversion before scale",
        ],
        "risk_reversal": "Satisfaction guarantee or trial window tied to top objection.",
        "positioning_statement": f"We help the target audience achieve the plan goal for {goal[:120]}.",
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
        f"Offer strategy for {data.plan_goal[:200]}\n\n"
        "## Core offer\n"
        f"{structured['core_offer']}\n",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured["value_proposition"]),
            prefix="Offer strategy (mock):",
        ),
    )


def _parse_content(content: str, data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Core offer",
            "Value proposition",
            "Unique mechanism",
            "Offer variants",
            "Pricing hypotheses",
            "Risk reversal",
            "Positioning statement",
        ),
    )
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "core_offer": sections.get("core_offer") or f"Core offer for {goal[:200]}",
        "value_proposition": sections.get("value_proposition") or "Value proposition from LLM output",
        "unique_mechanism": sections.get("unique_mechanism") or "Unique mechanism to be validated",
        "offer_variants": _list_from_section(
            sections.get("offer_variants") or "Primary offer variant",
        ),
        "pricing_hypotheses": _list_from_section(
            sections.get("pricing_hypotheses") or "Pricing hypothesis pending validation",
        ),
        "risk_reversal": sections.get("risk_reversal") or "Standard risk reversal to test",
        "positioning_statement": sections.get("positioning_statement")
        or f"Positioning aligned with {goal[:160]}",
    }


async def execute_offer_strategist_specialist(
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
            LLMMessage(role="system", content=_OFFER_STRATEGIST_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_message),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=build_specialist_llm_metadata(
            execution_run_id=str(sanitized.execution_run_id),
            task_index=sanitized.task_index,
            specialist=MarketingSpecialistType.OFFER_STRATEGIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Offer Strategist LLM returned empty content")
    body = truncate_content(output.content)
    structured = merge_structured_with_llm_meta(
        _parse_content(body, sanitized),
        provider=provider,
        model=model or output.model or "unknown",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured.get("value_proposition", "")),
            prefix="Offer strategy:",
        ),
    )


__all__ = [
    "OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS",
    "execute_offer_strategist_specialist",
    "prior_output_from_row",
]

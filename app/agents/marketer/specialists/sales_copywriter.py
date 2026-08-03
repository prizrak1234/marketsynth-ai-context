"""Sales Copywriter specialist execution (Phase AI.114) — sales copy only, not posts."""

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
    "You are a sales copywriter for BotFazer. Write direct-response sales copy only.\n"
    "Not social posts — landing/sales page sections using offer and research context.\n"
    "Do not request tools. Respond in markdown with:\n"
    "## Summary\n"
    "## Headline\n"
    "## Offer\n"
    "## Objections\n"
    "## Benefits\n"
    "## CTA\n"
    "## Sales sections\n"
)

_TITLE = "Sales copy"
_OUTPUT_TYPE = "sales_copy"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
}

SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS = (
    "headline",
    "offer",
    "objections",
    "benefits",
    "cta",
    "sales_sections",
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
            "Sales Copywriter execution requires prior offer and researcher context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "headline": f"Get results aligned with {data.plan_goal[:120]}",
        "offer": "Core offer package with clear outcome promise and risk reversal",
        "objections": [
            "Will this work for my situation?",
            "Is the price justified by outcomes?",
        ],
        "benefits": [
            "Faster path to the plan goal",
            "Reduced risk with proof and guarantee",
        ],
        "cta": "Book a discovery call / Start now",
        "sales_sections": [
            {"section": "Hero", "focus": "Headline + primary CTA"},
            {"section": "Proof", "focus": "Evidence and testimonials"},
            {"section": "Offer stack", "focus": "Deliverables and bonus value"},
            {"section": "Close", "focus": "CTA with risk reversal"},
        ],
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
        f"## Headline\n{structured['headline']}\n\n## Offer\n{structured['offer']}\n",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured["headline"]),
            prefix="Sales copy (mock):",
        ),
    )


def _parse_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        ("Headline", "Offer", "Objections", "Benefits", "CTA", "Sales sections"),
    )
    return {
        "headline": sections.get("headline") or "Primary sales headline",
        "offer": sections.get("offer") or "Core offer summary",
        "objections": _list_from_section(sections.get("objections") or "Top buyer objection"),
        "benefits": _list_from_section(sections.get("benefits") or "Primary buyer benefit"),
        "cta": sections.get("cta") or "Primary call to action",
        "sales_sections": _list_from_section(
            sections.get("sales_sections") or "Hero section\nProof section\nClose section",
        ),
    }


async def execute_sales_copywriter_specialist(
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
            specialist=MarketingSpecialistType.SALES_COPYWRITER,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Sales Copywriter LLM returned empty content")
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
            str(structured.get("headline", "")),
            prefix="Sales copy:",
        ),
    )


__all__ = [
    "SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS",
    "execute_sales_copywriter_specialist",
    "prior_output_from_row",
]

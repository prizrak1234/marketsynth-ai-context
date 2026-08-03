"""Lead Magnet Specialist execution (Phase AI.113) — concepts only, no assets."""

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
from app.agents.marketer.specialists.funnel_architect import (
    FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS,
)
from app.agents.marketer.specialists.offer_strategist import (
    OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
)
from app.agents.marketer.specialists.researcher import prior_output_from_row
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
    "You are a lead magnet specialist for BotFazer. Propose lead capture concepts only.\n"
    "Use offer strategy and funnel design — do not generate files or landing pages.\n"
    "Do not request tools. Respond in markdown with:\n"
    "## Summary\n"
    "## Lead magnet type\n"
    "## Title variants\n"
    "## Promise\n"
    "## Delivery format\n"
    "## Qualification goal\n"
    "## Followup recommendation\n"
)

_TITLE = "Lead magnet concept"
_OUTPUT_TYPE = "lead_magnet"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.FUNNEL_ARCHITECT,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.FUNNEL_ARCHITECT: FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS,
}

LEAD_MAGNET_PRIOR_STRUCTURED_KEYS = (
    "lead_magnet_type",
    "title_variants",
    "promise",
    "delivery_format",
    "qualification_goal",
    "followup_recommendation",
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
            "Lead Magnet Specialist requires prior offer and funnel context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "lead_magnet_type": "Checklist",
        "title_variants": [
            "5-step checklist to reach your goal faster",
            "The practical guide prospects ask for first",
        ],
        "promise": f"Quick win aligned with {data.plan_goal[:160]}",
        "delivery_format": "PDF checklist delivered by email opt-in",
        "qualification_goal": "Identify prospects ready for the core offer conversation",
        "followup_recommendation": "Nurture with proof email then offer invitation",
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
        f"Lead magnet for {data.plan_goal[:200]}\n\n"
        f"## Promise\n{structured['promise']}\n",
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured["promise"]),
            prefix="Lead magnet (mock):",
        ),
    )


def _parse_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Lead magnet type",
            "Title variants",
            "Promise",
            "Delivery format",
            "Qualification goal",
            "Followup recommendation",
        ),
    )
    return {
        "lead_magnet_type": sections.get("lead_magnet_type") or "Checklist",
        "title_variants": _list_from_section(
            sections.get("title_variants") or "Lead magnet title variant",
        ),
        "promise": sections.get("promise") or "Clear outcome promise for opt-in",
        "delivery_format": sections.get("delivery_format") or "Digital download via email",
        "qualification_goal": sections.get("qualification_goal") or "Qualify intent for core offer",
        "followup_recommendation": sections.get("followup_recommendation")
        or "Follow up with nurture sequence",
    }


async def execute_lead_magnet_specialist(
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
            specialist=MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Lead Magnet Specialist LLM returned empty content")
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
            str(structured.get("promise", "")),
            prefix="Lead magnet:",
        ),
    )


__all__ = [
    "LEAD_MAGNET_PRIOR_STRUCTURED_KEYS",
    "execute_lead_magnet_specialist",
    "prior_output_from_row",
]

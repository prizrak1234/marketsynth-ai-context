"""Email/DM Specialist execution (Phase AI.115) — nurture sequences only."""

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
from app.agents.marketer.specialists.researcher import prior_output_from_row
from app.agents.marketer.specialists.sales_copywriter import (
    SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS,
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
    "You are an email/DM nurture specialist for BotFazer. Design warm-up sequences only.\n"
    "Use offer strategy and sales copy — no sending, automation, or bot dispatch.\n"
    "Do not request tools. Respond in markdown with:\n"
    "## Summary\n"
    "## Sequence steps\n"
    "## Message goals\n"
    "## CTA map\n"
    "## Trigger points\n"
    "## Followup rules\n"
)

_TITLE = "Email/DM sequence"
_OUTPUT_TYPE = "email_sequence"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.SALES_COPYWRITER: SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS,
}

EMAIL_DM_PRIOR_STRUCTURED_KEYS = (
    "sequence_steps",
    "message_goals",
    "cta_map",
    "trigger_points",
    "followup_rules",
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
            "Email/DM Specialist requires prior offer and sales copy context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "sequence_steps": [
            "Day 0 — Welcome + value delivery",
            "Day 2 — Proof and objection handling",
            "Day 5 — Offer invitation",
            "Day 8 — Follow-up for non-responders",
        ],
        "message_goals": [
            "Build trust after opt-in",
            "Reinforce offer value proposition",
            "Drive primary conversion CTA",
        ],
        "cta_map": {
            "step_1": "Reply with your top challenge",
            "step_3": "Book call / purchase offer",
        },
        "trigger_points": [
            "Opt-in completed",
            "Link click without conversion",
            "No open after 48 hours",
        ],
        "followup_rules": [
            "Pause sequence on conversion",
            "Send one re-engagement message after 7 days idle",
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
        "## Summary\n"
        f"Nurture sequence for {data.plan_goal[:200]}\n\n"
        "## Sequence steps\n"
        + "\n".join(f"- {step}" for step in structured["sequence_steps"]),
    )
    return MarketingSpecialistExecutionOutput(
        title=_TITLE,
        output_type=_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured["sequence_steps"][0]),
            prefix="Email sequence (mock):",
        ),
    )


def _parse_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Sequence steps",
            "Message goals",
            "CTA map",
            "Trigger points",
            "Followup rules",
        ),
    )
    return {
        "sequence_steps": _list_from_section(
            sections.get("sequence_steps") or "Step 1 welcome\nStep 2 nurture",
        ),
        "message_goals": _list_from_section(
            sections.get("message_goals") or "Build trust\nDrive conversion",
        ),
        "cta_map": {"primary": sections.get("cta_map") or "Primary CTA per step"},
        "trigger_points": _list_from_section(
            sections.get("trigger_points") or "Opt-in trigger",
        ),
        "followup_rules": _list_from_section(
            sections.get("followup_rules") or "Follow up after no response",
        ),
    }


async def execute_email_dm_specialist(
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
            specialist=MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("Email/DM Specialist LLM returned empty content")
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
            str(structured["sequence_steps"][0]),
            prefix="Email sequence:",
        ),
    )


__all__ = [
    "EMAIL_DM_PRIOR_STRUCTURED_KEYS",
    "execute_email_dm_specialist",
    "prior_output_from_row",
]

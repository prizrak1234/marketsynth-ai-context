"""SMM Strategist execution (Phase AI.117) — strategy only, no scheduling."""

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
    CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
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

_TITLE = "SMM strategy"
_OUTPUT_TYPE = "smm_strategy"
_REQUIRED_PRIOR = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.OFFER_STRATEGIST,
)
_PRIOR_KEYS = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CONTENT_PLANNER: CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
}

SMM_PRIOR_STRUCTURED_KEYS = (
    "platform_focus",
    "content_formats",
    "posting_frequency",
    "engagement_hooks",
    "community_management_notes",
    "social_proof_ideas",
    "risks",
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
            "SMM Strategist requires strategist, researcher, planner, and offer context",
        )


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    return {
        "platform_focus": ["Telegram community", "Instagram reels", "LinkedIn thought leadership"],
        "content_formats": ["Short tips", "Before/after proof", "FAQ carousels"],
        "posting_frequency": ["Telegram: 4x/week", "Instagram: 3x/week", "LinkedIn: 2x/week"],
        "engagement_hooks": ["Poll on top pain", "Ask-me-anything thread", "Client win spotlight"],
        "community_management_notes": [
            "Reply within 24h on DMs",
            "Pin offer FAQ in Telegram",
        ],
        "social_proof_ideas": ["Screenshot testimonials", "Mini case study posts"],
        "risks": ["Inconsistent cadence without content planner alignment"],
    }


async def execute_smm_strategist_specialist(
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
        content = truncate_content("## Summary\nSMM strategy aligned to offer and content plan.\n")
        return MarketingSpecialistExecutionOutput(
            title=_TITLE,
            output_type=_OUTPUT_TYPE,
            content=content,
            structured_data=structured,
            safe_summary=safe_summary_from_content(
                ", ".join(structured["platform_focus"][:2]),
                prefix="SMM (mock):",
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
                content="You are an SMM strategist for BotFazer. Strategy only — no posting or tools.",
            ),
            LLMMessage(role="user", content=user_message),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=build_specialist_llm_metadata(
            execution_run_id=str(sanitized.execution_run_id),
            task_index=sanitized.task_index,
            specialist=MarketingSpecialistType.SMM_STRATEGIST,
        ),
    )
    output = await adapter.generate(llm_input)
    reject_tool_calls(output.tool_calls)
    if not (output.content or "").strip():
        raise ExecutorError("SMM Strategist LLM returned empty content")
    body = truncate_content(output.content)
    sections = parse_markdown_sections(
        body,
        (
            "Platform focus",
            "Content formats",
            "Posting frequency",
            "Engagement hooks",
            "Community management notes",
            "Social proof ideas",
            "Risks",
        ),
    )
    structured = merge_structured_with_llm_meta(
        {
            "platform_focus": _list_from_section(sections.get("platform_focus") or "Primary platform"),
            "content_formats": _list_from_section(sections.get("content_formats") or "Short-form post"),
            "posting_frequency": _list_from_section(
                sections.get("posting_frequency") or "3 posts per week",
            ),
            "engagement_hooks": _list_from_section(
                sections.get("engagement_hooks") or "Question hook",
            ),
            "community_management_notes": _list_from_section(
                sections.get("community_management_notes") or "Reply to DMs daily",
            ),
            "social_proof_ideas": _list_from_section(
                sections.get("social_proof_ideas") or "Testimonial post",
            ),
            "risks": _list_from_section(sections.get("risks") or "Cadence risk"),
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
            ", ".join(structured["platform_focus"][:2]),
            prefix="SMM:",
        ),
    )


__all__ = ["SMM_PRIOR_STRUCTURED_KEYS", "execute_smm_strategist_specialist", "prior_output_from_row"]

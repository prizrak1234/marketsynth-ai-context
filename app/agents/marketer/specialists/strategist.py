"""Strategist specialist dry-run execution (Phase AI.31)."""

from __future__ import annotations

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
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMMessage
from app.llm.registry import get_llm_adapter
from app.marketing.strategy_contracts import build_mock_strategy_draft_body
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistType,
)

_STRATEGIST_SYSTEM_PROMPT = (
    "You are a marketing strategist for BotFazer. Produce strategic direction only.\n"
    "Do not request tools. Respond in markdown with these sections:\n"
    "## Summary\n"
    "## Positioning\n"
    "## Target audience\n"
    "## Key message\n"
    "## Strategic risks\n"
    "## Next specialists\n"
    "Keep recommendations actionable and aligned with the plan goal."
)

_STRATEGIST_TITLE = "Strategic direction"
_STRATEGIST_OUTPUT_TYPE = "strategy"


def _default_next_specialists() -> list[str]:
    return [
        MarketingSpecialistType.RESEARCHER.value,
        MarketingSpecialistType.CONTENT_PLANNER.value,
    ]


def _build_user_message(data: MarketingSpecialistExecutionInput) -> str:
    return (
        f"Plan goal:\n{data.plan_goal}\n\n"
        f"Task objective:\n{data.objective}\n\n"
        f"Expected output:\n{data.expected_output}\n\n"
        f"Project context:\n{format_project_context_block(data.project_context)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_STRATEGIST_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "positioning": (
            f"Clear positioning for {goal[:240]} — emphasize trust and measurable outcomes."
        ),
        "target_audience": (
            "Primary audience segments from the approved plan snapshot; refine with research next."
        ),
        "key_message": (
            "Lead with the core value proposition, then proof points aligned to the plan goal."
        ),
        "strategic_risks": [
            "Message-market fit not yet validated with fresh research.",
            "Channel mix may be under-specified until content planning runs.",
        ],
        "next_specialists": _default_next_specialists(),
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
    content = truncate_content(build_mock_strategy_draft_body())
    return MarketingSpecialistExecutionOutput(
        title=_STRATEGIST_TITLE,
        output_type=_STRATEGIST_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            structured["positioning"],
            prefix="Strategic direction (mock):",
        ),
    )


def _parse_strategist_content(
    content: str,
    data: MarketingSpecialistExecutionInput,
) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Positioning",
            "Target audience",
            "Key message",
            "Strategic risks",
            "Next specialists",
        ),
    )
    positioning = sections.get("positioning") or (
        f"Strategic positioning aligned with: {data.plan_goal[:300]}"
    )
    target_audience = sections.get("target_audience") or (
        "Target audience to be refined with researcher input."
    )
    key_message = sections.get("key_message") or (
        "Key message should reinforce the plan goal in customer language."
    )
    risks_raw = sections.get("strategic_risks") or ""
    strategic_risks = [
        line.strip("- ").strip()
        for line in risks_raw.splitlines()
        if line.strip()
    ] or ["Execution dependencies on downstream specialists remain."]
    next_raw = sections.get("next_specialists") or ""
    next_specialists = [
        part.strip().lower().replace(" ", "_")
        for part in next_raw.replace(",", "\n").splitlines()
        if part.strip()
    ] or _default_next_specialists()
    return {
        "positioning": positioning,
        "target_audience": target_audience,
        "key_message": key_message,
        "strategic_risks": strategic_risks,
        "next_specialists": next_specialists,
    }


def _build_from_llm_content(
    content: str,
    data: MarketingSpecialistExecutionInput,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    body = truncate_content(content)
    structured = merge_structured_with_llm_meta(
        _parse_strategist_content(body, data),
        provider=provider,
        model=model,
    )
    return MarketingSpecialistExecutionOutput(
        title=_STRATEGIST_TITLE,
        output_type=_STRATEGIST_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(structured.get("positioning", "")),
            prefix="Strategic direction:",
        ),
    )


async def execute_strategist_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Run strategist LLM path (or deterministic mock) — no tools, no child runs."""
    sanitized = sanitize_execution_input(data)
    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.STRATEGIST,
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
        raise ExecutorError("Strategist LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        sanitized,
        provider=provider,
        model=model or output.model or "unknown",
    )

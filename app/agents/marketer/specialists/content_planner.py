"""Content Planner specialist execution (Phase AI.33) — structure only, no copy."""

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
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMMessage
from app.llm.registry import get_llm_adapter
from app.marketing.content_plan_quality import build_mock_content_plan_body
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)

_CONTENT_PLANNER_SYSTEM_PROMPT = (
    "You are a content planner for BotFazer. Build a content plan structure only.\n"
    "Use the plan goal, task brief, project context, strategist direction, "
    "and researcher insights.\n"
    "Do not write final post copy, ads, or emails — only pillars, funnel mapping, ideas, "
    "sequence, channels, and copywriter dependencies.\n"
    "Do not request tools or web search.\n"
    "Respond in markdown with these sections:\n"
    "## Summary\n"
    "## Content pillars\n"
    "## Funnel stages\n"
    "## Post ideas\n"
    "## Publishing sequence\n"
    "## Channel recommendations\n"
    "## Dependencies for copywriter\n"
    "## Risks\n"
)

_PLANNER_TITLE = "Content plan"
_PLANNER_OUTPUT_TYPE = "content_plan"

_REQUIRED_PRIOR_SPECIALISTS = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
)


def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    if not prior_outputs:
        return "No prior specialist outputs."
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        blocks.append(
            json.dumps(
                {
                    "specialist": item.specialist.value,
                    "title": item.title,
                    "output_type": item.output_type,
                    "safe_summary": item.safe_summary,
                    "structured_data": structured,
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
        f"Prior strategist and researcher outputs:\n"
        f"{_format_prior_outputs_block(data.prior_outputs)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_CONTENT_PLANNER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _prior_specialist_present(
    prior_outputs: list[MarketingSpecialistPriorOutput],
    specialist: MarketingSpecialistType,
) -> bool:
    return any(item.specialist == specialist for item in prior_outputs)


def _list_from_section(raw: str) -> list[str]:
    items = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return items or ([raw.strip()] if raw.strip() else [])


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    strategist = next(
        (p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.STRATEGIST),
        None,
    )
    researcher = next(
        (p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.RESEARCHER),
        None,
    )
    positioning = ""
    if strategist and strategist.structured_data:
        positioning = str(strategist.structured_data.get("positioning", ""))[:160]
    pains = []
    if researcher and researcher.structured_data:
        raw_pains = researcher.structured_data.get("pains")
        if isinstance(raw_pains, list):
            pains = [str(item) for item in raw_pains[:2]]
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "content_pillars": [
            f"Trust and proof for {goal[:80]}",
            "Education before conversion",
            "Objection handling via researcher insights",
        ],
        "funnel_stages": [
            "Awareness — introduce positioning",
            "Consideration — address pains and desires",
            "Conversion — reinforce key message",
        ],
        "post_ideas": [
            {
                "title": "Positioning explainer",
                "channel": "blog",
                "funnel_stage": "awareness",
                "brief": positioning or "Align with strategist direction",
            },
            {
                "title": "Pain-point FAQ",
                "channel": "social",
                "funnel_stage": "consideration",
                "brief": pains[0] if pains else "Draw from researcher pains list",
            },
            {
                "title": "Proof-led CTA outline",
                "channel": "email",
                "funnel_stage": "conversion",
                "brief": "Structure only — copywriter drafts final text",
            },
        ],
        "publishing_sequence": [
            "Week 1: awareness blog + social teaser",
            "Week 2: consideration FAQ thread",
            "Week 3: conversion email outline handoff to copywriter",
        ],
        "channel_recommendations": [
            "Owned blog for depth",
            "Social for objection surfacing",
            "Email for conversion narrative structure",
        ],
        "dependencies_for_copywriter": [
            "Copywriter drafts final post copy for each post_ideas item",
            "Tone aligned to strategist key_message",
            "CTA variants per funnel stage — no assets created in this phase",
        ],
        "risks": [
            "Plan assumes desk research only — validate channels with real performance data later",
            "No calendar scheduling or asset generation in this phase",
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
    content = truncate_content(build_mock_content_plan_body(goal=data.plan_goal))
    pillars = structured["content_pillars"]
    summary_seed = pillars[0] if pillars else "Content plan"
    return MarketingSpecialistExecutionOutput(
        title=_PLANNER_TITLE,
        output_type=_PLANNER_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(summary_seed),
            prefix="Content plan (mock):",
        ),
    )


def _parse_planner_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Content pillars",
            "Funnel stages",
            "Post ideas",
            "Publishing sequence",
            "Channel recommendations",
            "Dependencies for copywriter",
            "Risks",
        ),
    )
    return {
        "content_pillars": _list_from_section(
            sections.get("content_pillars") or "Core education and proof pillars",
        ),
        "funnel_stages": _list_from_section(
            sections.get("funnel_stages") or "Awareness, consideration, conversion",
        ),
        "post_ideas": _list_from_section(
            sections.get("post_ideas") or "Outline ideas only — copywriter drafts text",
        ),
        "publishing_sequence": _list_from_section(
            sections.get("publishing_sequence") or "Sequence TBD with stakeholder review",
        ),
        "channel_recommendations": _list_from_section(
            sections.get("channel_recommendations") or "Blog, social, email",
        ),
        "dependencies_for_copywriter": _list_from_section(
            sections.get("dependencies_for_copywriter")
            or "Final copy per outlined idea — no assets in this phase",
        ),
        "risks": _list_from_section(
            sections.get("risks") or "Assumptions require validation before publish",
        ),
    }


def _build_from_llm_content(
    content: str,
    *,
    provider: LLMProvider,
    model: str,
) -> MarketingSpecialistExecutionOutput:
    body = truncate_content(content)
    structured = merge_structured_with_llm_meta(
        _parse_planner_content(body),
        provider=provider,
        model=model,
    )
    pillars = structured["content_pillars"]
    summary_seed = pillars[0] if pillars else body[:200]
    return MarketingSpecialistExecutionOutput(
        title=_PLANNER_TITLE,
        output_type=_PLANNER_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            str(summary_seed),
            prefix="Content plan:",
        ),
    )


def validate_content_planner_prior_outputs(
    prior_outputs: list[MarketingSpecialistPriorOutput],
) -> None:
    if not _prior_specialist_present(prior_outputs, MarketingSpecialistType.STRATEGIST):
        raise ExecutorError("Content Planner execution requires prior strategist context")
    if not _prior_specialist_present(prior_outputs, MarketingSpecialistType.RESEARCHER):
        raise ExecutorError("Content Planner execution requires prior researcher context")


async def execute_content_planner_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Content plan structure from strategist + researcher — no copy or assets."""
    sanitized = sanitize_execution_input(data)
    validate_content_planner_prior_outputs(sanitized.prior_outputs)

    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.CONTENT_PLANNER,
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
        raise ExecutorError("Content Planner LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        provider=provider,
        model=model or output.model or "unknown",
    )


"""Researcher specialist desk-research execution (Phase AI.32) — no web/tools."""

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
from app.core.security import sanitize_text
from app.llm.contracts import LLMMessage
from app.llm.registry import get_llm_adapter
from app.marketing.research_quality import build_mock_research_body
from app.schemas.contracts import (
    LLMProvider,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistPriorOutput,
    MarketingSpecialistType,
)

_RESEARCHER_SYSTEM_PROMPT = (
    "You are a marketing researcher for BotFazer performing desk research only.\n"
    "Use only the plan goal, task brief, project context, and prior strategist output.\n"
    "Do not request tools, web search, or external data. Label assumptions explicitly.\n"
    "Respond in markdown with these sections:\n"
    "## Summary\n"
    "## Audience segments\n"
    "## Pains\n"
    "## Desires\n"
    "## Objections\n"
    "## Market assumptions\n"
    "## Research gaps\n"
    "## Recommended next questions\n"
)

_RESEARCHER_TITLE = "Audience and market research"
_RESEARCHER_OUTPUT_TYPE = "research"
_PRIOR_CONTENT_EXCERPT_MAX = 2400

STRATEGIST_PRIOR_STRUCTURED_KEYS = (
    "positioning",
    "target_audience",
    "key_message",
    "strategic_risks",
    "next_specialists",
)

RESEARCHER_PRIOR_STRUCTURED_KEYS = (
    "audience_segments",
    "pains",
    "desires",
    "objections",
    "market_assumptions",
    "research_gaps",
    "recommended_next_questions",
)

CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS = (
    "content_pillars",
    "funnel_stages",
    "post_ideas",
    "publishing_sequence",
    "channel_recommendations",
    "dependencies_for_copywriter",
    "risks",
)

COPYWRITER_PRIOR_STRUCTURED_KEYS = ("content_items",)

CRITIC_PRIOR_STRUCTURED_KEYS = (
    "strengths",
    "weaknesses",
    "inconsistencies",
    "missing_information",
    "improvement_actions",
    "approval_recommendation",
)

OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS = (
    "core_offer",
    "value_proposition",
    "unique_mechanism",
    "offer_variants",
    "pricing_hypotheses",
    "risk_reversal",
    "positioning_statement",
)

FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS = (
    "funnel_stages",
    "entry_points",
    "lead_capture",
    "nurture_sequence",
    "conversion_events",
    "retention_actions",
)

LEAD_MAGNET_PRIOR_STRUCTURED_KEYS = (
    "lead_magnet_type",
    "title_variants",
    "promise",
    "delivery_format",
    "qualification_goal",
    "followup_recommendation",
)

SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS = (
    "headline",
    "offer",
    "objections",
    "benefits",
    "cta",
    "sales_sections",
)

EMAIL_DM_PRIOR_STRUCTURED_KEYS = (
    "sequence_steps",
    "message_goals",
    "cta_map",
    "trigger_points",
    "followup_rules",
)

CRO_PRIOR_STRUCTURED_KEYS = (
    "conversion_bottlenecks",
    "landing_page_recommendations",
    "cta_improvements",
    "trust_elements",
    "form_optimization",
    "test_hypotheses",
    "priority_actions",
)

SMM_PRIOR_STRUCTURED_KEYS = (
    "platform_focus",
    "content_formats",
    "posting_frequency",
    "engagement_hooks",
    "community_management_notes",
    "social_proof_ideas",
    "risks",
)

AD_CREATIVE_PRIOR_STRUCTURED_KEYS = (
    "creative_angles",
    "ad_hooks",
    "visual_concepts",
    "primary_text_variants",
    "headline_variants",
    "cta_variants",
    "testing_matrix",
)

_PRIOR_STRUCTURED_KEYS_BY_SPECIALIST = {
    MarketingSpecialistType.STRATEGIST: STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.RESEARCHER: RESEARCHER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CONTENT_PLANNER: CONTENT_PLANNER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.COPYWRITER: COPYWRITER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CRITIC: CRITIC_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.OFFER_STRATEGIST: OFFER_STRATEGIST_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.FUNNEL_ARCHITECT: FUNNEL_ARCHITECT_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST: LEAD_MAGNET_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.SALES_COPYWRITER: SALES_COPYWRITER_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.EMAIL_DM_SPECIALIST: EMAIL_DM_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.CRO_SPECIALIST: CRO_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.SMM_STRATEGIST: SMM_PRIOR_STRUCTURED_KEYS,
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST: AD_CREATIVE_PRIOR_STRUCTURED_KEYS,
}

_LLM_META_KEYS = frozenset({"llm_provider", "model", "mock"})


def _format_prior_outputs_block(prior_outputs: list[MarketingSpecialistPriorOutput]) -> str:
    if not prior_outputs:
        return "No prior specialist outputs."
    blocks: list[str] = []
    for item in prior_outputs:
        structured = item.structured_data or {}
        allowed = _PRIOR_STRUCTURED_KEYS_BY_SPECIALIST.get(item.specialist, ())
        safe_structured = {key: structured[key] for key in allowed if key in structured}
        blocks.append(
            json.dumps(
                {
                    "specialist": item.specialist.value,
                    "title": item.title,
                    "output_type": item.output_type,
                    "safe_summary": item.safe_summary,
                    "structured_data": safe_structured,
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
        f"Prior specialist outputs (desk research only):\n"
        f"{_format_prior_outputs_block(data.prior_outputs)}"
    )


def _build_messages(data: MarketingSpecialistExecutionInput) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=_RESEARCHER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=_build_user_message(data)),
    ]


def _list_from_section(raw: str) -> list[str]:
    items = [
        line.strip("- ").strip()
        for line in raw.splitlines()
        if line.strip()
    ]
    return items or [raw.strip()] if raw.strip() else []


def _mock_structured_data(data: MarketingSpecialistExecutionInput) -> dict[str, Any]:
    strategist = next(
        (p for p in data.prior_outputs if p.specialist == MarketingSpecialistType.STRATEGIST),
        None,
    )
    positioning = ""
    if strategist and strategist.structured_data:
        positioning = str(strategist.structured_data.get("positioning", ""))[:200]
    goal = data.plan_goal.strip() or "the approved marketing plan"
    return {
        "audience_segments": [
            "Primary segment aligned with the approved plan goal",
            "Secondary segment needing proof before conversion",
        ],
        "pains": [
            "Uncertainty about offer fit without live market interviews",
            "Friction from incomplete channel clarity",
        ],
        "desires": [
            "Clear outcomes tied to the plan goal",
            "Trust signals before committing budget",
        ],
        "objections": [
            "Skepticism until researcher gaps are validated externally",
            "Price/value clarity depends on positioning follow-through",
        ],
        "market_assumptions": [
            (
                "Desk research assumes strategist positioning "
                f"({positioning[:120] or goal[:120]}) holds."
            ),
            "No web or tool verification was performed in this phase.",
        ],
        "research_gaps": [
            "No primary customer interviews logged in project context",
            "Competitive pricing signals not available without external research phase",
        ],
        "recommended_next_questions": [
            "Which segment converts fastest with the current offer?",
            "What proof assets reduce the top objection before copywriting?",
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
    topic = data.objective[:120] or "desk research"
    content = truncate_content(
        build_mock_research_body(goal=data.plan_goal, research_topic=topic),
    )
    summary_seed = ", ".join(structured["audience_segments"][:2])
    return MarketingSpecialistExecutionOutput(
        title=_RESEARCHER_TITLE,
        output_type=_RESEARCHER_OUTPUT_TYPE,
        content=content,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            summary_seed,
            prefix="Desk research (mock):",
        ),
    )


def _parse_researcher_content(content: str) -> dict[str, Any]:
    sections = parse_markdown_sections(
        content,
        (
            "Audience segments",
            "Pains",
            "Desires",
            "Objections",
            "Market assumptions",
            "Research gaps",
            "Recommended next questions",
        ),
    )
    return {
        "audience_segments": _list_from_section(
            sections.get("audience_segments") or "General audience from plan context",
        ),
        "pains": _list_from_section(sections.get("pains") or "Pain points require validation"),
        "desires": _list_from_section(sections.get("desires") or "Desired outcomes from plan goal"),
        "objections": _list_from_section(
            sections.get("objections") or "Objections not yet validated externally",
        ),
        "market_assumptions": _list_from_section(
            sections.get("market_assumptions")
            or "Assumptions derived from in-project context only",
        ),
        "research_gaps": _list_from_section(
            sections.get("research_gaps") or "External validation still required",
        ),
        "recommended_next_questions": _list_from_section(
            sections.get("recommended_next_questions")
            or "What evidence would confirm the top segment choice?",
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
        _parse_researcher_content(body),
        provider=provider,
        model=model,
    )
    summary_seed = ", ".join(structured["audience_segments"][:2])
    return MarketingSpecialistExecutionOutput(
        title=_RESEARCHER_TITLE,
        output_type=_RESEARCHER_OUTPUT_TYPE,
        content=body,
        structured_data=structured,
        safe_summary=safe_summary_from_content(
            summary_seed,
            prefix="Desk research:",
        ),
    )


async def execute_researcher_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    """Desk research from plan + strategist context — no web, tools, or child runs."""
    sanitized = sanitize_execution_input(data)
    if not sanitized.prior_outputs:
        raise ExecutorError("Researcher execution requires prior strategist context")

    provider, model, temperature, max_tokens = resolve_project_llm_config()

    if provider == LLMProvider.MOCK:
        return _build_mock_output(sanitized, provider=provider, model=model)

    adapter = get_llm_adapter(provider)
    metadata = build_specialist_llm_metadata(
        execution_run_id=str(sanitized.execution_run_id),
        task_index=sanitized.task_index,
        specialist=MarketingSpecialistType.RESEARCHER,
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
        raise ExecutorError("Researcher LLM returned empty content")
    return _build_from_llm_content(
        output.content,
        provider=provider,
        model=model or output.model or "unknown",
    )


def prior_output_from_row(
    *,
    specialist: MarketingSpecialistType,
    title: str,
    output_type: str,
    content: str,
    structured_data: dict[str, Any] | None,
) -> MarketingSpecialistPriorOutput:
    """Build safe prior context from a persisted specialist output row."""
    safe_structured: dict[str, Any] | None = None
    if structured_data:
        allowed = _PRIOR_STRUCTURED_KEYS_BY_SPECIALIST.get(specialist, ())
        safe_structured = {key: structured_data[key] for key in allowed if key in structured_data}
        for key in _LLM_META_KEYS:
            safe_structured.pop(key, None)
    excerpt = sanitize_text(content).strip()[:_PRIOR_CONTENT_EXCERPT_MAX]
    summary = None
    if safe_structured:
        if specialist == MarketingSpecialistType.STRATEGIST and safe_structured.get("positioning"):
            summary = safe_summary_from_content(
                str(safe_structured["positioning"]),
                prefix="Strategist:",
            )
        elif specialist == MarketingSpecialistType.RESEARCHER:
            segments = safe_structured.get("audience_segments")
            if isinstance(segments, list) and segments:
                summary = safe_summary_from_content(str(segments[0]), prefix="Researcher:")
        elif specialist == MarketingSpecialistType.CONTENT_PLANNER:
            ideas = safe_structured.get("post_ideas")
            if isinstance(ideas, list) and ideas:
                first = ideas[0]
                label = first.get("title", str(first)) if isinstance(first, dict) else str(first)
                summary = safe_summary_from_content(str(label)[:200], prefix="Planner:")
        elif specialist == MarketingSpecialistType.COPYWRITER:
            items = safe_structured.get("content_items")
            if isinstance(items, list) and items:
                first_item = items[0]
                headline = (
                    first_item.get("headline", str(first_item))
                    if isinstance(first_item, dict)
                    else str(first_item)
                )
                summary = safe_summary_from_content(str(headline)[:200], prefix="Copy:")
        elif specialist == MarketingSpecialistType.CRITIC:
            rec = safe_structured.get("approval_recommendation")
            if rec:
                summary = safe_summary_from_content(str(rec), prefix="Critique:")
        elif specialist == MarketingSpecialistType.OFFER_STRATEGIST:
            vp = safe_structured.get("value_proposition")
            if vp:
                summary = safe_summary_from_content(str(vp), prefix="Offer:")
        elif specialist == MarketingSpecialistType.FUNNEL_ARCHITECT:
            stages = safe_structured.get("funnel_stages")
            if isinstance(stages, list) and stages:
                summary = safe_summary_from_content(str(stages[0]), prefix="Funnel:")
        elif specialist == MarketingSpecialistType.LEAD_MAGNET_SPECIALIST:
            promise = safe_structured.get("promise")
            if promise:
                summary = safe_summary_from_content(str(promise), prefix="Lead magnet:")
        elif specialist == MarketingSpecialistType.SALES_COPYWRITER:
            headline = safe_structured.get("headline")
            if headline:
                summary = safe_summary_from_content(str(headline), prefix="Sales copy:")
        elif specialist == MarketingSpecialistType.EMAIL_DM_SPECIALIST:
            steps = safe_structured.get("sequence_steps")
            if isinstance(steps, list) and steps:
                summary = safe_summary_from_content(str(steps[0]), prefix="Email sequence:")
        elif specialist == MarketingSpecialistType.CRO_SPECIALIST:
            actions = safe_structured.get("priority_actions")
            if isinstance(actions, list) and actions:
                summary = safe_summary_from_content(str(actions[0]), prefix="CRO:")
        elif specialist == MarketingSpecialistType.SMM_STRATEGIST:
            platforms = safe_structured.get("platform_focus")
            if isinstance(platforms, list) and platforms:
                summary = safe_summary_from_content(str(platforms[0]), prefix="SMM:")
        elif specialist == MarketingSpecialistType.AD_CREATIVE_STRATEGIST:
            angles = safe_structured.get("creative_angles")
            if isinstance(angles, list) and angles:
                summary = safe_summary_from_content(str(angles[0]), prefix="Ad creative:")
    return MarketingSpecialistPriorOutput(
        specialist=specialist,
        title=title,
        output_type=output_type,
        safe_summary=summary,
        structured_data=safe_structured or None,
        content_excerpt=excerpt or None,
    )

"""Marketing skill executors (Phase AI.229–AI.233)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

SkillExecutorResult = tuple[dict[str, Any], dict[str, Any], list[UUID]]


async def execute_segment_research(
    _session: AsyncSession,
    _owner_id: UUID,
    _project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context

    ctx = parse_skill_context(payload)
    segment = ctx.segment_name or ctx.target_audience or "Target segment"
    industry = ctx.industry or "general services"
    geo = ctx.geography or "local market"
    offer = ctx.offer or "core service package"

    output = {
        "soc_dem": f"Adults interested in {industry}; decision-makers for {offer[:80]}",
        "geo": geo,
        "pains": [
            "Hard to compare providers and prices",
            "Low trust in advertising claims",
            "Fear of hidden costs or poor quality",
        ],
        "desires": [
            "Clear outcome and transparent pricing",
            "Fast response and convenient booking",
            "Proof from similar customers nearby",
        ],
        "fears": [
            "Making the wrong provider choice",
            "Wasting budget on low-quality leads",
        ],
        "current_state": f"{segment} searches online but hesitates without proof and clarity",
        "desired_state": f"{segment} chooses a trusted {industry} provider with a clear offer",
        "research_questions": [
            f"What search queries does {segment} use for {industry}?",
            f"Which objections block conversion to {offer[:60]}?",
            f"Which geo areas show highest intent in {geo}?",
        ],
    }
    return output, {"provider": "mock_skill", "skill_step": "segment_research"}, []


async def execute_meaning_unpacking(
    _session: AsyncSession,
    _owner_id: UUID,
    _project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context

    ctx = parse_skill_context(payload)
    offer = ctx.offer or "Premium service package"
    audience = ctx.target_audience or "Local customers"

    output = {
        "desires_table": [
            {"desire": "Save time", "signal": "Wants quick booking and clear next step"},
            {"desire": "Reduce risk", "signal": "Needs proof, reviews, guarantees"},
            {"desire": "Get result", "signal": f"Expects measurable outcome from {offer[:60]}"},
        ],
        "benefit_mapping": [
            {"feature": offer[:80], "benefit": "Predictable outcome without guesswork"},
            {"feature": "Local expertise", "benefit": "Fits context of " + audience[:60]},
        ],
        "fear_objection_table": [
            {"fear": "Too expensive", "objection": "Price without value proof"},
            {"fear": "Low quality", "objection": "No reviews or case studies"},
        ],
        "counter_arguments": [
            "Show price breakdown vs expected result",
            "Use local case studies and before/after proof",
        ],
        "promise_formulations": [
            f"Get a clear plan for {offer[:50]} in one consultation",
            f"{audience[:40]} get trusted {ctx.industry or 'service'} without hidden fees",
        ],
    }
    return output, {"provider": "mock_skill", "skill_step": "meaning_unpacking"}, []


async def execute_offer_packaging(
    _session: AsyncSession,
    _owner_id: UUID,
    _project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context

    ctx = parse_skill_context(payload)
    offer = ctx.offer or "Core service package"
    industry = ctx.industry or "local business"

    output = {
        "measurable_result": f"Qualified leads or booked consultations for {industry}",
        "speed": "First contact within 24 hours; onboarding in 3–5 days",
        "mechanism": f"Structured funnel around {offer[:70]} with proof and CTA",
        "simplicity": "One landing page, one primary CTA, one follow-up sequence",
        "safety": "Transparent pricing block and review/social proof section",
        "core_thesis": (
            f"{offer[:90]} solves the main pain of "
            f"{ctx.target_audience or 'target audience'}"
        ),
        "offer_variants": [
            {"name": "Starter", "focus": "Entry package with limited scope"},
            {"name": "Standard", "focus": offer[:80]},
            {"name": "Premium", "focus": "Extended scope with priority support"},
        ],
    }
    return output, {"provider": "mock_skill", "skill_step": "offer_packaging"}, []


async def execute_offer_justification(
    _session: AsyncSession,
    _owner_id: UUID,
    _project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context

    ctx = parse_skill_context(payload)
    offer = ctx.offer or "Core service package"
    audience = ctx.target_audience or "Target customers"

    output = {
        "target_fit": f"Built for {audience[:80]} in {ctx.geography or 'your market'}",
        "how_it_works": f"Attract → qualify → convert with offer: {offer[:70]}",
        "why_it_works": "Combines clear promise, proof, and low-friction CTA",
        "convenience_blocks": [
            "Online booking or callback form",
            "FAQ covering top 5 objections",
        ],
        "safety_proof": [
            "Reviews/testimonials section",
            "Guarantee or trial terms if applicable",
        ],
        "value_breakdown": [
            {"item": "Strategy + setup", "value": "Saves weeks of trial and error"},
            {"item": "Execution support", "value": "Reduces cost of poor targeting"},
        ],
        "price_justification": "Price reflects outcome focus, not hourly labor",
        "final_cta": f"Book a consultation to validate fit for {offer[:50]}",
    }
    return output, {"provider": "mock_skill", "skill_step": "offer_justification"}, []


async def execute_wordstat_research(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context
    from app.schemas.contracts import MarketingToolType
    from app.services.marketing_tool_call_service import MarketingToolCallService

    ctx = parse_skill_context(payload)
    query = _optional_text(payload.get("query")) or ctx.offer or ctx.industry or "marketing demand"
    used_ids: list[UUID] = []
    wordstat_summary: dict[str, Any] | None = None

    if payload.get("create_tool_call") is True:
        tool_row = await MarketingToolCallService(session).create_call(
            owner_id,
            project_id,
            MarketingToolType.WORDSTAT,
            {
                "query": query[:512],
                "region": ctx.geography,
                "report_type": payload.get("report_type") or "one",
            },
        )
        if tool_row is not None and tool_row.output_payload:
            used_ids.append(tool_row.id)
            wordstat_summary = dict(tool_row.output_payload)

    shows = 0
    if wordstat_summary and wordstat_summary.get("rows"):
        shows = int(wordstat_summary["rows"][0].get("shows") or 0)

    output = {
        "query": query,
        "business_conclusion": (
            f"Search demand for '{query[:60]}' looks "
            f"{'strong' if shows >= 800 else 'moderate' if shows >= 300 else 'niche'} "
            "— validate with landing tests before scaling spend."
        ),
        "demand_signal": "strong" if shows >= 800 else "moderate" if shows >= 300 else "niche",
        "wordstat_summary": wordstat_summary
        or {"provider": "mock", "note": "Set create_tool_call=true to attach Wordstat tool output"},
        "recommended_next_steps": [
            "Compare 3–5 query variants in Wordstat",
            "Map top queries to landing page headlines",
        ],
    }
    return output, {"provider": "mock_skill", "external_tool_used": bool(used_ids)}, used_ids


async def execute_metrica_analysis(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context
    from app.schemas.contracts import MarketingToolType
    from app.services.marketing_tool_call_service import MarketingToolCallService

    ctx = parse_skill_context(payload)
    used_ids: list[UUID] = []
    metrica_summary: dict[str, Any] | None = None

    if payload.get("create_tool_call") is True:
        tool_row = await MarketingToolCallService(session).create_call(
            owner_id,
            project_id,
            MarketingToolType.METRICA,
            {
                "metrics": payload.get("metrics") or ["visits", "users", "pageviews"],
                "dimensions": payload.get("dimensions") or ["traffic", "device"],
                "natural_language": payload.get("natural_language")
                or f"traffic analysis for {ctx.industry or 'campaign'}",
                "counter_id": payload.get("counter_id"),
            },
        )
        if tool_row is not None and tool_row.output_payload:
            used_ids.append(tool_row.id)
            metrica_summary = dict(tool_row.output_payload)

    output = {
        "business_conclusion": (
            "Site traffic shows mixed channels — prioritize channels with "
            "higher visit-to-lead conversion before increasing budget."
        ),
        "metrica_summary": metrica_summary
        or {"provider": "mock", "note": "Set create_tool_call=true to attach Metrica tool output"},
        "focus_metrics": ["visits", "users", "conversion to lead"],
        "recommended_next_steps": [
            "Review traffic source vs device breakdown",
            "Fix landing pages with high bounce on mobile",
        ],
    }
    return output, {"provider": "mock_skill", "external_tool_used": bool(used_ids)}, used_ids


async def execute_visual_report(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    payload: dict[str, Any],
) -> SkillExecutorResult:
    from app.marketing.skills.context import parse_skill_context
    from app.schemas.contracts import MarketingToolType
    from app.services.marketing_tool_call_service import MarketingToolCallService

    ctx = parse_skill_context(payload)
    prompt = _optional_text(payload.get("prompt")) or (
        f"Marketing visual for {ctx.industry or 'business'}: {ctx.offer or 'core offer'}"
    )
    used_ids: list[UUID] = []
    images: list[dict[str, Any]] = []

    if payload.get("create_tool_call") is True:
        tool_row = await MarketingToolCallService(session).create_call(
            owner_id,
            project_id,
            MarketingToolType.IMAGE_GENERATION,
            {"prompt": prompt[:4096], "aspect_ratio": payload.get("aspect_ratio") or "16:9"},
        )
        if tool_row is not None and tool_row.output_payload:
            used_ids.append(tool_row.id)
            images = list(tool_row.output_payload.get("images") or [])

    output = {
        "report_title": f"Visual direction — {ctx.industry or 'campaign'}",
        "summary": "Mock visual report for creative alignment before production.",
        "creative_brief": prompt[:500],
        "layout_blocks": [
            "Hero with primary promise",
            "Proof strip (reviews / logos)",
            "Offer + CTA block",
        ],
        "images": images,
        "business_conclusion": "Use one hero visual and one proof-led variant for A/B testing.",
    }
    return output, {"provider": "mock_skill", "external_tool_used": bool(used_ids)}, used_ids


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

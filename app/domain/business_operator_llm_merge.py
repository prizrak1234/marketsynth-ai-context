"""Merge rule-based and LLM business intent (Phase AI.200)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.business_intent_analyzer import (
    _INDUSTRY_TO_BUSINESS_TYPE,
    _INDUSTRY_TO_SCENARIO,
    IntentAnalysisResult,
)
from app.domain.business_operator_clarifications import GOAL_OPTIONS, INDUSTRY_OPTIONS
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import (
    BusinessIntent,
    BusinessOperatorIntentSource,
    BusinessOperatorLLMIntent,
)


@dataclass(frozen=True, slots=True)
class ResolvedBusinessIntent:
    intent: BusinessIntent
    source: BusinessOperatorIntentSource
    confidence_before: float
    confidence_after: float
    industry_keyword_score: int
    goal_keyword_score: int
    llm_used: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None


def validate_llm_intent(llm_intent: BusinessOperatorLLMIntent) -> bool:
    """Reject LLM output with unknown scenario or invalid enums."""
    if (
        llm_intent.suggested_scenario is not None
        and get_scenario(llm_intent.suggested_scenario) is None
    ):
        return False
    if llm_intent.industry is not None and llm_intent.industry not in INDUSTRY_OPTIONS:
        return False
    if llm_intent.goal not in GOAL_OPTIONS:
        return False
    return bool(llm_intent.reasoning_summary.strip())


def business_intent_from_llm(llm_intent: BusinessOperatorLLMIntent) -> BusinessIntent:
    """Convert validated LLM intent into BusinessIntent contract."""
    industry = llm_intent.industry or "local"
    goal = llm_intent.goal
    scenario_id = llm_intent.suggested_scenario or _INDUSTRY_TO_SCENARIO.get(
        industry,
        "local_service_promo",
    )
    if get_scenario(scenario_id) is None:
        scenario_id = _INDUSTRY_TO_SCENARIO.get(industry, "local_service_promo")

    return BusinessIntent(
        goal=goal,
        industry=industry,
        business_type=llm_intent.business_type or _INDUSTRY_TO_BUSINESS_TYPE.get(industry),
        campaign_type=llm_intent.campaign_type or goal,
        confidence=round(llm_intent.confidence, 2),
        recommended_scenario=scenario_id,
    )


def resolve_rule_based(analysis: IntentAnalysisResult) -> ResolvedBusinessIntent:
    """Use rule-based intent only."""
    confidence = analysis.intent.confidence
    return ResolvedBusinessIntent(
        intent=analysis.intent,
        source=BusinessOperatorIntentSource.RULE_BASED,
        confidence_before=confidence,
        confidence_after=confidence,
        industry_keyword_score=analysis.industry_keyword_score,
        goal_keyword_score=analysis.goal_keyword_score,
    )


def resolve_clarification(analysis: IntentAnalysisResult) -> ResolvedBusinessIntent:
    """Fall back to clarification path with rule-based intent."""
    confidence = analysis.intent.confidence
    return ResolvedBusinessIntent(
        intent=analysis.intent,
        source=BusinessOperatorIntentSource.CLARIFICATION,
        confidence_before=confidence,
        confidence_after=confidence,
        industry_keyword_score=analysis.industry_keyword_score,
        goal_keyword_score=analysis.goal_keyword_score,
    )


def resolve_llm_fallback(
    analysis: IntentAnalysisResult,
    llm_intent: BusinessOperatorLLMIntent,
    *,
    llm_provider: str,
    llm_model: str,
) -> ResolvedBusinessIntent:
    """Apply LLM classification when it beats rule confidence."""
    merged = business_intent_from_llm(llm_intent)
    return ResolvedBusinessIntent(
        intent=merged,
        source=BusinessOperatorIntentSource.LLM_FALLBACK,
        confidence_before=analysis.intent.confidence,
        confidence_after=merged.confidence,
        industry_keyword_score=1,
        goal_keyword_score=1,
        llm_used=True,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

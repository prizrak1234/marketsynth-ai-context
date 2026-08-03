"""Clarification questions and answer merging (Phase AI.187–AI.189)."""

from __future__ import annotations

from app.domain.business_intent_analyzer import (
    _INDUSTRY_DEFAULT_GOAL,
    _INDUSTRY_TO_BUSINESS_TYPE,
    _INDUSTRY_TO_SCENARIO,
)
from app.schemas.contracts import BusinessIntent, BusinessOperatorClarification

INDUSTRY_OPTIONS: tuple[str, ...] = ("dental", "restaurant", "expert", "saas", "local")
GOAL_OPTIONS: tuple[str, ...] = ("lead_generation", "launch", "content", "promo")

_INDUSTRY_QUESTION = BusinessOperatorClarification(
    question="What industry is your business in?",
    reason="We need your industry to recommend the right marketing scenario.",
    missing_field="industry",
    options=list(INDUSTRY_OPTIONS),
    required=True,
)

_GOAL_QUESTION = BusinessOperatorClarification(
    question="What is your primary business goal?",
    reason="Your goal helps us pick specialists and expected deliverables.",
    missing_field="goal",
    options=list(GOAL_OPTIONS),
    required=True,
)


def build_clarification_questions(
    intent: BusinessIntent,
    *,
    industry_keyword_score: int,
    goal_keyword_score: int,
) -> list[BusinessOperatorClarification]:
    """Return clarifications for fields that were not detected confidently."""
    questions: list[BusinessOperatorClarification] = []
    if industry_keyword_score == 0:
        questions.append(_INDUSTRY_QUESTION)
    if goal_keyword_score == 0:
        questions.append(_GOAL_QUESTION)
    if not questions and intent.confidence < 0.65:
        questions.append(_INDUSTRY_QUESTION)
    return questions


def apply_clarification_answers(
    previous: BusinessIntent,
    answers: dict[str, str],
) -> BusinessIntent:
    """Merge user clarification answers into intent and boost confidence."""
    industry = previous.industry or "local"
    goal = previous.goal or _INDUSTRY_DEFAULT_GOAL.get(industry, "promo")

    if "industry" in answers:
        candidate = answers["industry"].strip().lower()
        if candidate in INDUSTRY_OPTIONS:
            industry = candidate

    if "goal" in answers:
        candidate = answers["goal"].strip().lower()
        if candidate in GOAL_OPTIONS:
            goal = candidate

    scenario_id = _INDUSTRY_TO_SCENARIO.get(industry, "local_service_promo")
    business_type = _INDUSTRY_TO_BUSINESS_TYPE.get(industry)

    confidence = previous.confidence
    if "industry" in answers and answers["industry"].strip().lower() in INDUSTRY_OPTIONS:
        confidence = max(confidence + 0.25, 0.70)
    if "goal" in answers and answers["goal"].strip().lower() in GOAL_OPTIONS:
        confidence = max(confidence + 0.15, 0.68)
    if "industry" in answers and "goal" in answers:
        confidence = max(confidence, 0.75)

    return BusinessIntent(
        goal=goal,
        industry=industry,
        business_type=business_type,
        campaign_type=goal,
        confidence=round(min(1.0, confidence), 2),
        recommended_scenario=scenario_id,
    )

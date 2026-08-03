"""Campaign brief completeness scoring and questions (Phase AI.208–AI.209)."""

from __future__ import annotations

from app.core.config import get_settings
from app.domain.business_operator_clarifications import GOAL_OPTIONS, INDUSTRY_OPTIONS
from app.schemas.contracts import CampaignBriefCompleteness, CampaignBriefFields, CampaignBriefQuestion

_REQUIRED_FIELDS: tuple[str, ...] = ("industry", "offer", "target_audience", "goal")
_OPTIONAL_FIELDS: tuple[str, ...] = ("geography", "channels", "budget_range", "deadline")
_FIELD_WEIGHT = 25

_QUESTIONS: dict[str, CampaignBriefQuestion] = {
    "industry": CampaignBriefQuestion(
        field="industry",
        question="What industry is your business in?",
        options=list(INDUSTRY_OPTIONS),
        required=True,
    ),
    "offer": CampaignBriefQuestion(
        field="offer",
        question="What product or service are you promoting?",
        required=True,
    ),
    "target_audience": CampaignBriefQuestion(
        field="target_audience",
        question="Who is your target audience?",
        required=True,
    ),
    "goal": CampaignBriefQuestion(
        field="goal",
        question="What is the primary campaign goal?",
        options=list(GOAL_OPTIONS),
        required=True,
    ),
    "geography": CampaignBriefQuestion(
        field="geography",
        question="Which city or region are you targeting?",
        required=False,
    ),
    "channels": CampaignBriefQuestion(
        field="channels",
        question="Which channels do you want to focus on? (comma-separated)",
        options=["telegram", "instagram", "email", "offline", "paid_ads"],
        required=False,
    ),
    "budget_range": CampaignBriefQuestion(
        field="budget_range",
        question="What is your approximate budget range?",
        options=["under_500", "500_2000", "2000_10000", "10000_plus"],
        required=False,
    ),
    "deadline": CampaignBriefQuestion(
        field="deadline",
        question="When do you need first results?",
        required=False,
    ),
}


def _field_filled(brief: CampaignBriefFields, field: str) -> bool:
    value = getattr(brief, field)
    if isinstance(value, list):
        return bool(value)
    return value is not None and str(value).strip() != ""


def evaluate_brief_completeness(brief: CampaignBriefFields) -> CampaignBriefCompleteness:
    """Score required brief fields 0–100 and return missing questions."""
    score = 0
    missing: list[CampaignBriefQuestion] = []
    for field in _REQUIRED_FIELDS:
        if _field_filled(brief, field):
            score += _FIELD_WEIGHT
        else:
            missing.append(_QUESTIONS[field])

    for field in _OPTIONAL_FIELDS:
        if not _field_filled(brief, field):
            missing.append(_QUESTIONS[field])

    threshold = get_settings().campaign_brief_completeness_threshold
    required_missing = [question for question in missing if question.required]
    passed = score >= threshold and not required_missing
    return CampaignBriefCompleteness(
        score=min(score, 100),
        threshold=threshold,
        passed=passed,
        missing_questions=missing,
    )

"""PRODUCT-01.3B.2A — commercial relevance gate for evidence and findings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.business_idea_validation.coverage_categories import normalize_category
from app.business_idea_validation.research_decomposition import decompose_intake
from app.schemas.contracts import BusinessIdeaValidationInput

_COMMERCIAL_DOMAIN = frozenset(
    {
        "ai",
        "martech",
        "marketing",
        "маркетинг",
        "automation",
        "автоматиза",
        "saas",
        "agency",
        "агентств",
        "platform",
        "платформ",
        "software",
        "generative",
        "контент",
        "content",
        "campaign",
        "кампан",
        "seo",
        "реклам",
        "analytics",
        "аналит",
    }
)

_GENERIC_ECONOMY = frozenset(
    {
        "блогер",
        "blogger",
        "youtube",
        "influencer",
        "инфлюенс",
        "сегмент российской экономики",
        "38%",
        "бренд",
    }
)

_VIABILITY_QUESTIONS = frozenset(
    {
        "market",
        "demand",
        "competitors",
        "audience",
        "pricing",
        "commercial_risks",
        "local_context",
    }
)


@dataclass(frozen=True, slots=True)
class CommercialRelevanceAssessment:
    relevant: bool
    rationale: str


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{2,}", (text or "").lower()))


def assess_commercial_relevance(
    *,
    inp: BusinessIdeaValidationInput,
    category: str,
    observation: str,
) -> CommercialRelevanceAssessment:
    canonical = normalize_category(category)
    if canonical not in _VIABILITY_QUESTIONS:
        return CommercialRelevanceAssessment(relevant=True, rationale="non_viability_category")

    blob = observation.lower()
    obs_tokens = _tokens(blob)
    commercial_hits = obs_tokens & _COMMERCIAL_DOMAIN
    generic_hits = obs_tokens & _GENERIC_ECONOMY

    decomp = decompose_intake(inp)
    context_tokens = _tokens(
        " ".join(
            [
                decomp.use_case,
                decomp.core_search_subject,
                decomp.payer_segment,
                decomp.replacement_target,
            ]
        )
    )
    context_overlap = len(context_tokens & obs_tokens)

    # Reject macro economy / influencer stats without product linkage
    if generic_hits and len(commercial_hits) < 2:
        if canonical in {"market", "demand", "competitors", "pricing", "commercial_risks"}:
            return CommercialRelevanceAssessment(
                relevant=False,
                rationale="generic_audience_economy_not_product_viability",
            )

    if canonical == "audience":
        has_pain = any(
            t in blob
            for t in (
                "боль",
                "проблем",
                "задач",
                "pain",
                "challenge",
                "need",
                "потреб",
                "затрат",
                "время",
            )
        )
        if generic_hits and not has_pain and len(commercial_hits) < 1:
            return CommercialRelevanceAssessment(
                relevant=False,
                rationale="audience_stat_without_problem_or_product_link",
            )

    if len(commercial_hits) == 0 and context_overlap < 2:
        return CommercialRelevanceAssessment(
            relevant=False,
            rationale="no_commercial_domain_overlap",
        )

    if canonical in {"market", "demand"} and len(commercial_hits) < 1:
        return CommercialRelevanceAssessment(
            relevant=False,
            rationale="market_demand_without_commercial_signal",
        )

    return CommercialRelevanceAssessment(relevant=True, rationale="commercially_relevant")

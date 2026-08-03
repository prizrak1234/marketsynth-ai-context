"""PRODUCT-01.3B — relevance gate for fetched sources vs analysis context."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.business_idea_validation.research_decomposition import decompose_intake
from app.business_idea_validation.sanitization import domain_from_url
from app.schemas.contracts import (
    BusinessIdeaValidationInput,
    BusinessIdeaValidationSourceClass,
)

_GENERIC_SEO_HOSTS = (
    "skillbox.ru",
    "netology.ru",
    "youtube.com",
    "youtu.be",
    "google.com",
    "yandex.ru",
    "wikipedia.org",
    "reddit.com",
    "vk.com",
    "instagram.com",
    "facebook.com",
    "t.me",
)

_GENERIC_LANDING_HINTS = (
    "курсы",
    "обучение",
    "запишитесь",
    "скидка",
    "промокод",
    "online course",
    "sign up",
    "subscribe",
    "outsourcing",
    "аутсорс",
)


@dataclass(frozen=True, slots=True)
class RelevanceAssessment:
    relevant: bool
    score: float
    rationale: str


def _tokens(text: str) -> set[str]:
    parts = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{2,}", (text or "").lower())
    return set(parts)


_COMMERCIAL_HINTS = (
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
    "generative",
    "контент",
    "content",
    "campaign",
    "кампан",
)


def assess_source_relevance(
    *,
    inp: BusinessIdeaValidationInput,
    url: str,
    title: str,
    body_excerpt: str,
    source_class: BusinessIdeaValidationSourceClass,
) -> RelevanceAssessment:
    host = domain_from_url(url) or ""
    blob = f"{title} {body_excerpt[:600]}".lower()

    low_tier_classes = {
        BusinessIdeaValidationSourceClass.USER_GENERATED,
        BusinessIdeaValidationSourceClass.COMMERCIAL_BLOG,
        BusinessIdeaValidationSourceClass.UNKNOWN,
    }
    if any(h in host for h in _GENERIC_SEO_HOSTS) and source_class in low_tier_classes:
        return RelevanceAssessment(
            relevant=False,
            score=0.1,
            rationale="generic_platform_or_education_landing",
        )

    if any(h in blob for h in _GENERIC_LANDING_HINTS):
        idea_tokens = _tokens(inp.idea)
        overlap = len(idea_tokens & _tokens(blob))
        if overlap < 2:
            return RelevanceAssessment(
                relevant=False,
                score=0.15,
                rationale="generic_landing_without_idea_overlap",
            )

    context_blob = " ".join(
        filter(
            None,
            [
                inp.idea,
                inp.market,
                inp.location,
                inp.target_audience,
                inp.product_or_service,
            ],
        )
    ).lower()
    decomp = decompose_intake(inp)
    context_blob = " ".join(
        [
            context_blob,
            decomp.use_case,
            decomp.core_search_subject,
            decomp.payer_segment,
            decomp.replacement_target,
        ]
    ).lower()
    context_tokens = _tokens(context_blob)
    source_tokens = _tokens(f"{title} {body_excerpt[:400]}")
    if not context_tokens:
        return RelevanceAssessment(relevant=True, score=0.5, rationale="no_context_tokens")

    commercial_in_source = any(h in blob for h in _COMMERCIAL_HINTS)
    if not commercial_in_source and len(source_tokens & context_tokens) < 2:
        return RelevanceAssessment(
            relevant=False,
            score=0.12,
            rationale="no_commercial_domain_overlap",
        )

    overlap_ratio = len(context_tokens & source_tokens) / max(len(context_tokens), 1)
    if inp.location:
        loc_tokens = _tokens(inp.location)
        if loc_tokens & source_tokens:
            overlap_ratio += 0.15
    if inp.target_audience:
        aud_tokens = _tokens(inp.target_audience)
        if aud_tokens & source_tokens:
            overlap_ratio += 0.1

    if overlap_ratio < 0.08:
        return RelevanceAssessment(
            relevant=False,
            score=min(overlap_ratio, 0.2),
            rationale="low_context_overlap",
        )

    return RelevanceAssessment(
        relevant=True,
        score=min(0.95, 0.35 + overlap_ratio),
        rationale="context_overlap_ok",
    )

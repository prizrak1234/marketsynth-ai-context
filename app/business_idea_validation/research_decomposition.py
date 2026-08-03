"""PRODUCT-01.3B.2A — decompose intake into research-ready commercial context."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.contracts import BusinessIdeaValidationInput

_UNKNOWN_MARKERS = frozenset(
    {
        "unknown",
        "неизвестно",
        "не известно",
        "неизвестны",
        "не указано",
        "n/a",
        "na",
        "-",
    }
)

_GENERIC_PRODUCT_LABELS = frozenset({"saas", "b2b saas", "b2b", "software", "софт"})


@dataclass(frozen=True, slots=True)
class ResearchIntakeDecomposition:
    use_case: str
    product_delivery: str
    payer_segment: str
    geography: str
    replacement_target: str
    alternatives: str | None
    pricing_hypothesis: str | None
    core_search_subject: str
    clarification_needed: tuple[str, ...] = field(default_factory=tuple)


def _is_unknown(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return True
    return normalized in _UNKNOWN_MARKERS


def _dedupe_words(text: str) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for word in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9\-]+", text):
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        words.append(word)
    return " ".join(words)


def _extract_use_case(idea: str) -> str:
    cleaned = re.sub(r"\s+", " ", idea.strip())
    if len(cleaned) <= 160:
        return cleaned
    first = re.split(r"[.;]\s+", cleaned, maxsplit=1)[0]
    return first[:160].strip()


def _infer_replacement(idea: str) -> str:
    lower = idea.lower()
    if "агентств" in lower:
        return "традиционное маркетинговое агентство"
    if "сотрудник" in lower or "in-house" in lower:
        return "штатный маркетолог"
    if "набор" in lower or "сервис" in lower:
        return "набор маркетинговых сервисов"
    return "ручные маркетинговые процессы"


def decompose_intake(inp: BusinessIdeaValidationInput) -> ResearchIntakeDecomposition:
    idea = inp.idea.strip()
    use_case = _extract_use_case(idea)
    product_delivery = (inp.market or inp.product_or_service or "SaaS").strip()
    payer = (inp.target_audience or "").strip()
    geography = (inp.location or inp.market or "").strip()
    if geography.lower() in _GENERIC_PRODUCT_LABELS:
        geography = (inp.location or "").strip()

    competitors_raw = (inp.known_competitors or inp.constraints or "").strip()
    alternatives = None if _is_unknown(competitors_raw) else competitors_raw

    pricing = (inp.pricing_or_revenue_model or inp.budget or "").strip() or None

    if product_delivery.lower() in _GENERIC_PRODUCT_LABELS:
        core = _dedupe_words(use_case)
    else:
        core = _dedupe_words(f"{use_case} {product_delivery}")

    clarification: list[str] = []
    if not payer:
        clarification.append("payer_segment")
    if len(use_case) < 24:
        clarification.append("use_case")
    if _is_unknown(competitors_raw):
        clarification.append("alternatives")

    return ResearchIntakeDecomposition(
        use_case=use_case,
        product_delivery=product_delivery,
        payer_segment=payer,
        geography=geography,
        replacement_target=_infer_replacement(idea),
        alternatives=alternatives,
        pricing_hypothesis=pricing,
        core_search_subject=core[:220],
        clarification_needed=tuple(clarification),
    )

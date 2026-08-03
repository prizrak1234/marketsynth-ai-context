"""Extract claims from fetched source text — no LLM, no search snippets."""

from __future__ import annotations

import re

from app.core.exceptions import InvalidStateError
from app.domain.evidence_fingerprint import validate_atomic_claim
from app.business_idea_validation.sanitization import sanitize_source_body
from app.schemas.contracts import EvidenceAssessmentState

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "market": (
        "market",
        "growth",
        "trend",
        "size",
        "рынок",
        "рост",
        "сегмент",
    ),
    "market_demand": (
        "demand",
        "market",
        "growth",
        "trend",
        "consumer",
        "спрос",
        "рынок",
        "рост",
    ),
    "demand": (
        "demand",
        "willingness",
        "interest",
        "adoption",
        "спрос",
        "интерес",
        "готовность",
    ),
    "competitors": (
        "compet",
        "rival",
        "alternative",
        "конкур",
        "альтернатив",
    ),
    "competition": (
        "compet",
        "rival",
        "price",
        "pricing",
        "конкур",
        "цена",
    ),
    "audience": (
        "audience",
        "customer",
        "segment",
        "buyer",
        "аудитор",
        "клиент",
        "покуп",
        "маркетолог",
        "блогер",
    ),
    "target_audience": (
        "audience",
        "customer",
        "segment",
        "buyer",
        "аудитор",
        "клиент",
        "покуп",
    ),
    "pricing": (
        "price",
        "pricing",
        "subscription",
        "tariff",
        "цена",
        "тариф",
        "подписк",
    ),
    "commercial_risks": (
        "risk",
        "regulat",
        "cost",
        "rent",
        "challenge",
        "риск",
        "аренд",
        "регулир",
    ),
    "local_context": (
        "local",
        "region",
        "district",
        "локаль",
        "регион",
    ),
}

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"you\s+are\s+now", re.I),
)


def sanitize_external_text(text: str, *, max_len: int = 8000) -> str:
    cleaned = " ".join((text or "").split())
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    return cleaned[:max_len]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 40]


def _to_atomic_claim(sentence: str) -> str | None:
    """Keep a single verifiable sentence that passes P0.4 atomic-claim rules."""
    first = re.split(r"[.!?]+", sentence.strip(), maxsplit=1)[0].strip()
    if len(first) < 8:
        return None
    try:
        return validate_atomic_claim(
            first,
            assessment_state=EvidenceAssessmentState.CONFIRMED,
        )
    except InvalidStateError:
        return None


def extract_claims(text: str, category: str) -> list[str]:
    """Return up to 2 substantive atomic claims from fetched body text."""
    safe = sanitize_source_body(text)
    if len(safe) < 40:
        return []

    keywords = _CATEGORY_KEYWORDS.get(category, ())
    claims: list[str] = []
    for sentence in _split_sentences(safe):
        lower = sentence.lower()
        if keywords and not any(k in lower for k in keywords):
            continue
        atomic = _to_atomic_claim(sentence)
        if atomic is None:
            continue
        claims.append(atomic[:500])
        if len(claims) >= 2:
            break

    if not claims:
        for sentence in _split_sentences(safe):
            atomic = _to_atomic_claim(sentence)
            if atomic is not None:
                claims.append(atomic[:500])
                if len(claims) >= 2:
                    break
    return claims


def detect_contradiction_pairs(claims: list[tuple[str, str]]) -> int:
    """Simple heuristic: high vs low demand language across sources."""
    high = ("high demand", "growing", "высокий спрос", "растущ")
    low = ("low demand", "declining", "низкий спрос", "падающ")
    has_high = any(any(h in c.lower() for h in high) for c, _ in claims)
    has_low = any(any(l in c.lower() for l in low) for c, _ in claims)
    return 1 if has_high and has_low else 0

"""Canonical research coverage category IDs — no internal BIV imports."""

from __future__ import annotations

from app.schemas.contracts import BusinessIdeaValidationInput

CANONICAL_CATEGORIES: tuple[str, ...] = (
    "market",
    "competitors",
    "audience",
    "demand",
    "pricing",
    "local_context",
    "commercial_risks",
)

LEGACY_CATEGORY_ALIASES: dict[str, str] = {
    "market_demand": "market",
    "competition": "competitors",
    "target_audience": "audience",
}

CATEGORY_LABELS_RU: dict[str, str] = {
    "market": "Рынок",
    "competitors": "Конкуренты",
    "audience": "Аудитория",
    "demand": "Спрос",
    "pricing": "Цена",
    "local_context": "Локальный контекст",
    "commercial_risks": "Коммерческие риски",
}


def normalize_category(category: str) -> str:
    normalized = (category or "").strip()
    return LEGACY_CATEGORY_ALIASES.get(normalized, normalized)


def required_categories(inp: BusinessIdeaValidationInput) -> list[str]:
    cats = list(CANONICAL_CATEGORIES)
    if not (inp.location or "").strip():
        cats = [c for c in cats if c != "local_context"]
    return cats

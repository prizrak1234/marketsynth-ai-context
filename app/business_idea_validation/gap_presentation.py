"""PRODUCT-01.3B.1 — customer-safe presentation for research gap diagnostic codes."""

from __future__ import annotations

import re

from app.schemas.contracts import BivResearchGapPresentation

_COVERAGE_PATTERN = re.compile(r"^coverage_(?P<category>[a-z_]+)_(?P<status>[a-z_]+)$")

_GAP_CATALOG: dict[str, tuple[str, str, str | None]] = {
    "fewer_than_3_fetched_sources": (
        "agency.biv.gap.fewerThan3Sources",
        "Найдено меньше трёх независимых источников. Уточните регион, сегмент клиента "
        "или известных конкурентов, затем запустите исследование повторно.",
        None,
    ),
    "fewer_than_3_independent_publishers": (
        "agency.biv.gap.fewerThan3Publishers",
        "Источники опираются на слишком мало независимых изданий. "
        "Добавьте конкурентов или уточните рынок.",
        "known_competitors",
    ),
    "fewer_than_3_evidence_records": (
        "agency.biv.gap.fewerThan3Evidence",
        "Подтверждённых фактов недостаточно для вывода.",
        None,
    ),
    "fewer_than_3_confirmed_evidence": (
        "agency.biv.gap.fewerThan3Confirmed",
        "Не найдено достаточно надёжных подтверждённых данных.",
        None,
    ),
    "missing_market_finding": (
        "agency.biv.gap.missingMarket",
        "Не удалось подтвердить данные о размере и динамике рынка.",
        "analysis_goal",
    ),
    "missing_demand_finding": (
        "agency.biv.gap.missingDemand",
        "Сигналы спроса и готовности платить не подтверждены источниками.",
        "analysis_goal",
    ),
    "missing_pricing_finding": (
        "agency.biv.gap.missingPricing",
        "Рыночные данные о ценах не найдены — указанная цена остаётся гипотезой.",
        "pricing_or_revenue_model",
    ),
    "missing_competitor_finding": (
        "agency.biv.gap.missingCompetitors",
        "Не удалось подтвердить данные о прямых конкурентах.",
        "known_competitors",
    ),
    "missing_audience_finding": (
        "agency.biv.gap.missingAudience",
        "Целевая аудитория не подтверждена источниками.",
        "target_customer",
    ),
    "missing_risk_finding": (
        "agency.biv.gap.missingRisks",
        "Коммерческие риски не подтверждены независимыми источниками.",
        None,
    ),
    "missing_local_context": (
        "agency.biv.gap.missingLocalContext",
        "Недостаточно локальных данных по выбранному региону.",
        "geography",
    ),
    "audience_hypothesis_only": (
        "agency.biv.gap.audienceHypothesis",
        "Аудитория указана как гипотеза — нужны подтверждающие источники.",
        "target_customer",
    ),
    "audience_inferred": (
        "agency.biv.gap.audienceInferred",
        "Аудитория выведена из текста идеи, но не подтверждена.",
        "target_customer",
    ),
    "business_verdict_missing": (
        "agency.biv.gap.verdictMissing",
        "Вердикт пока не сформирован — данных недостаточно для решения о запуске.",
        None,
    ),
    "generic_platform_or_education_landing": (
        "agency.biv.gap.genericLanding",
        "Найденные страницы не относятся к вашей идее (образовательные/рекламные площадки).",
        None,
    ),
    "generic_landing_without_idea_overlap": (
        "agency.biv.gap.noIdeaOverlap",
        "Источники не совпадают с описанием вашей идеи.",
        "idea_description",
    ),
    "low_context_overlap": (
        "agency.biv.gap.lowOverlap",
        "Источники слабо связаны с вашей идеей, аудиторией и регионом.",
        "idea_description",
    ),
    "tier_d_source_rejected": (
        "agency.biv.gap.tierDRejected",
        "Ненадёжные источники отфильтрованы и не использованы как доказательства.",
        None,
    ),
}

_CATEGORY_LABELS: dict[str, str] = {
    "market": "рынку",
    "market_demand": "рынку и спросу",
    "demand": "спросу",
    "competitors": "конкурентам",
    "competition": "конкурентам",
    "audience": "аудитории",
    "target_audience": "аудитории",
    "pricing": "ценам",
    "commercial_risks": "коммерческим рискам",
    "local_context": "локальному контексту",
}


def is_internal_gap_code(value: str) -> bool:
    """True when value looks like a backend diagnostic code, not user text."""
    normalized = (value or "").strip()
    if not normalized:
        return False
    if normalized in _GAP_CATALOG:
        return True
    if _COVERAGE_PATTERN.match(normalized):
        return True
    return bool(re.fullmatch(r"[a-z][a-z0-9_]{2,127}", normalized))


def present_research_gap(code: str) -> BivResearchGapPresentation:
    normalized = (code or "").strip()
    if not normalized:
        return BivResearchGapPresentation(
            code="unknown_gap",
            message_key="agency.biv.gap.unknown",
            customer_message="Недостаточно данных для этого блока исследования.",
        )

    match = _COVERAGE_PATTERN.match(normalized)
    if match:
        category = match.group("category")
        status = match.group("status")
        label = _CATEGORY_LABELS.get(category, category.replace("_", " "))
        if status == "insufficient":
            message = f"Недостаточно данных по {label}."
        elif status == "not_started":
            message = f"Блок «{label}» не был исследован."
        else:
            message = f"Пробел по {label}."
        return BivResearchGapPresentation(
            code=normalized,
            message_key="agency.biv.gap.coverageCategory",
            customer_message=message,
            recommended_action="Уточните контекст и повторите исследование.",
        )

    catalog = _GAP_CATALOG.get(normalized)
    if catalog:
        message_key, customer_message, intake_field = catalog
        return BivResearchGapPresentation(
            code=normalized,
            message_key=message_key,
            customer_message=customer_message,
            recommended_action=(
                "Уточните данные в форме и запустите исследование повторно."
                if intake_field
                else "Запустите исследование повторно после уточнения контекста."
            ),
            intake_field=intake_field,
        )

    if is_internal_gap_code(normalized):
        return BivResearchGapPresentation(
            code=normalized,
            message_key="agency.biv.gap.unknown",
            customer_message="Недостаточно данных для надёжного вывода по этому блоку.",
        )

    return BivResearchGapPresentation(
        code=normalized[:64],
        message_key="agency.biv.gap.custom",
        customer_message=normalized[:500],
    )


def present_research_gaps(codes: list[str]) -> list[BivResearchGapPresentation]:
    seen: set[str] = set()
    items: list[BivResearchGapPresentation] = []
    for raw in codes:
        code = (raw or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        items.append(present_research_gap(code))
    return items

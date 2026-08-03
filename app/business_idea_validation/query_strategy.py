"""PRODUCT-01.3B.2A — intake-aware search query generation."""

from __future__ import annotations

import re

from app.business_idea_validation.coverage_categories import CANONICAL_CATEGORIES
from app.business_idea_validation.research_decomposition import (
    ResearchIntakeDecomposition,
    decompose_intake,
)
from app.schemas.contracts import (
    BusinessIdeaValidationInput,
    BusinessIdeaValidationResearchPlanItem,
)


def _geo_phrase(decomp: ResearchIntakeDecomposition) -> str:
    geo = (decomp.geography or "").strip()
    if not geo:
        return ""
    lower = geo.lower()
    if any(t in lower for t in ("рф", "росс", "russia")):
        return "Россия"
    return geo


def _audience_phrase(decomp: ResearchIntakeDecomposition) -> str:
    return decomp.payer_segment or "маркетологи блогеры"


def _subject_short(decomp: ResearchIntakeDecomposition) -> str:
    """Core commercial subject — never bare 'SaaS' alone."""
    subject = decomp.core_search_subject
    if subject.lower() in ("saas", "b2b saas"):
        return "AI маркетинговое агентство автоматизация маркетинга"
    return subject[:180]


def _clean_query(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    # Drop unknown tokens that must never appear in search
    for bad in ("неизвестно", "unknown", "не указано", "n/a"):
        cleaned = re.sub(rf"\b{bad}\b", "", cleaned, flags=re.I)
    return cleaned[:512].strip()


def queries_for_category(
    decomp: ResearchIntakeDecomposition,
    category: str,
) -> list[tuple[str, str]]:
    geo = _geo_phrase(decomp)
    aud = _audience_phrase(decomp)
    subj = _subject_short(decomp)
    geo_suffix = f" {geo}" if geo else ""

    if category == "market":
        return [
            (
                _clean_query(f"рынок AI marketing software martech {geo_suffix}"),
                "Размер и динамика рынка AI/martech.",
            ),
            (
                _clean_query(f"рынок автоматизации маркетинга SaaS {geo_suffix} тренды"),
                "Сегмент marketing automation в регионе.",
            ),
        ]
    if category == "demand":
        return [
            (
                _clean_query(f"спрос автоматизация маркетинга {aud} {geo_suffix}"),
                "Сигналы спроса у целевой аудитории.",
            ),
            (
                _clean_query(f"generative AI маркетологи использование инструменты {geo_suffix}"),
                "Использование AI маркетологами.",
            ),
        ]
    if category == "competitors":
        alt = decomp.alternatives or "AI marketing automation платформы marketing agency SaaS"
        return [
            (
                _clean_query(f"конкуренты {subj} {alt} {geo_suffix}"),
                "Прямые и косвенные альтернативы.",
            ),
            (
                _clean_query(f"платформы автоматизации маркетингового агентства AI {geo_suffix}"),
                "Замена агентства AI-инструментами.",
            ),
        ]
    if category == "audience":
        return [
            (
                _clean_query(f"задачи боли {aud} AI инструменты маркетинг {geo_suffix}"),
                "Проблемы и задачи целевой аудитории.",
            ),
            (
                _clean_query(f"блогеры маркетологи создание контента автоматизация {geo_suffix}"),
                "Контент и продвижение у сегмента.",
            ),
        ]
    if category == "pricing":
        return [
            (
                _clean_query(f"цены тарифы AI marketing automation platforms subscription"),
                "Рыночные цены SaaS marketing automation.",
            ),
            (
                _clean_query(f"стоимость маркетингового агентства малый бизнес {geo_suffix}"),
                "Стоимость альтернативы — агентство.",
            ),
        ]
    if category == "local_context":
        return [
            (
                _clean_query(f"использование AI в маркетинге {geo_suffix}"),
                "Локальное adoption AI в маркетинге.",
            ),
            (
                _clean_query(f"регулирование AI сервисов маркетинг {geo_suffix}"),
                "Регуляторный и локальный контекст.",
            ),
        ]
    if category == "commercial_risks":
        return [
            (
                _clean_query(f"риски AI маркетинговых платформ SaaS {geo_suffix}"),
                "Коммерческие и продуктовые риски.",
            ),
            (
                _clean_query(f"причины отказа marketing automation SaaS churn"),
                "Барьеры и отток у automation SaaS.",
            ),
        ]
    return [(_clean_query(f"{subj} {category} {geo_suffix}"), f"Research track {category}.")]


def build_research_plan(inp: BusinessIdeaValidationInput) -> list[BusinessIdeaValidationResearchPlanItem]:
    """Round-1 plan: up to two intake-aware queries per research track."""
    decomp = decompose_intake(inp)
    items: list[BusinessIdeaValidationResearchPlanItem] = []

    for category in CANONICAL_CATEGORIES:
        if category == "local_context" and not (decomp.geography or inp.location):
            continue
        for query, rationale in queries_for_category(decomp, category):
            items.append(
                BusinessIdeaValidationResearchPlanItem(
                    category=category,
                    query=query,
                    rationale=rationale,
                    round_number=1,
                )
            )
    return items


def build_gap_queries(
    inp: BusinessIdeaValidationInput,
    missing_categories: list[str],
) -> list[BusinessIdeaValidationResearchPlanItem]:
    """Round-2: alternate query templates for missing tracks."""
    decomp = decompose_intake(inp)
    items: list[BusinessIdeaValidationResearchPlanItem] = []

    retry_templates: dict[str, list[tuple[str, str]]] = {
        "market": [
            (_clean_query(f"martech market size Russia AI marketing"), "Retry market sizing."),
            (_clean_query(f"статистика рынок digital marketing SaaS { _geo_phrase(decomp) }"), "Retry RF market stats."),
        ],
        "demand": [
            (_clean_query(f"willingness to pay marketing automation { _audience_phrase(decomp) }"), "Retry WTP signals."),
        ],
        "competitors": [
            (_clean_query(f"HubSpot Jasper Copy.ai marketing automation alternatives { _geo_phrase(decomp) }"), "Retry named alternatives."),
        ],
        "audience": [
            (_clean_query(f"marketing team pain points AI adoption survey"), "Retry audience pains."),
        ],
        "pricing": [
            (_clean_query(f"SaaS marketing automation pricing tiers monthly"), "Retry SaaS pricing."),
        ],
        "local_context": [
            (_clean_query(f"зарубежные маркетинговые платформы доступность { _geo_phrase(decomp) }"), "Retry local access."),
        ],
        "commercial_risks": [
            (_clean_query(f"AI generated marketing content legal risks"), "Retry content/legal risks."),
        ],
    }

    for category in missing_categories:
        templates = retry_templates.get(category) or queries_for_category(decomp, category)[-1:]
        for query, rationale in templates[:1]:
            items.append(
                BusinessIdeaValidationResearchPlanItem(
                    category=category,
                    query=query,
                    rationale=rationale,
                    round_number=2,
                    gap_directed=True,
                )
            )
    return items

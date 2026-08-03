"""CWF.1 — cascade research pipeline (direct → indirect → intl → local → adjacent)."""

from __future__ import annotations

from app.business_idea_validation.coverage_categories import CANONICAL_CATEGORIES
from app.business_idea_validation.query_strategy import _clean_query, queries_for_category
from app.business_idea_validation.research_decomposition import decompose_intake
from app.schemas.contracts import (
    BusinessIdeaValidationInput,
    BusinessIdeaValidationResearchPlanItem,
)

PIPELINE_PHASES: tuple[str, ...] = (
    "direct",
    "indirect",
    "international",
    "local",
    "adjacent",
    "transferability",
)

_PHASE_LABELS: dict[str, str] = {
    "direct": "Прямые источники",
    "indirect": "Косвенные подтверждения",
    "international": "Международная статистика",
    "local": "Локальная статистика",
    "adjacent": "Смежные рынки",
    "transferability": "Оценка переносимости данных",
}


def _phase_queries(
    *,
    phase: str,
    category: str,
    decomp,
    base_queries: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    geo = decomp.geography or ""
    geo_ru = "Россия" if any(t in geo.lower() for t in ("рф", "росс")) else geo
    subj = decomp.core_search_subject[:120]

    if phase == "direct":
        return base_queries[:1]

    if phase == "indirect":
        return [
            (
                _clean_query(f"тренды adoption {subj} case study"),
                "Косвенные сигналы через кейсы и обзоры.",
            ),
        ]

    if phase == "international":
        intl_map: dict[str, tuple[str, str]] = {
            "market": (
                _clean_query("global martech market size AI marketing automation report"),
                "Международные отчёты о рынке martech.",
            ),
            "demand": (
                _clean_query("marketers generative AI adoption survey statistics"),
                "Международные опросы маркетологов.",
            ),
            "competitors": (
                _clean_query("AI marketing platforms HubSpot Jasper Copy.ai market share"),
                "Международные конкуренты и альтернативы.",
            ),
            "audience": (
                _clean_query("marketing team pain points automation survey"),
                "Международные исследования болей аудитории.",
            ),
            "pricing": (
                _clean_query("marketing automation SaaS pricing benchmark report"),
                "Международные бенчмарки цен.",
            ),
            "local_context": (
                _clean_query(f"AI marketing regulation Europe US comparison {geo_ru}"),
                "Международный регуляторный контекст.",
            ),
            "commercial_risks": (
                _clean_query("AI marketing SaaS churn reasons market report"),
                "Международные риски и барьеры.",
            ),
        }
        item = intl_map.get(category)
        return [item] if item else []

    if phase == "local":
        if not geo_ru:
            return []
        local_map: dict[str, tuple[str, str]] = {
            "market": (
                _clean_query(f"рынок digital marketing SaaS статистика {geo_ru}"),
                "Локальная статистика рынка.",
            ),
            "demand": (
                _clean_query(f"маркетологи использование AI инструментов {geo_ru}"),
                "Локальные сигналы спроса.",
            ),
            "competitors": (
                _clean_query(f"российские платформы маркетинговой автоматизации {geo_ru}"),
                "Локальные конкуренты.",
            ),
            "audience": (
                _clean_query(f"боли маркетологов малый бизнес {geo_ru}"),
                "Локальный контекст аудитории.",
            ),
            "pricing": (
                _clean_query(f"стоимость маркетингового агентства малый бизнес {geo_ru}"),
                "Локальные цены альтернатив.",
            ),
            "local_context": (
                _clean_query(f"регулирование AI сервисов маркетинг {geo_ru}"),
                "Локальный регуляторный контекст.",
            ),
            "commercial_risks": (
                _clean_query(f"риски AI маркетинговых платформ {geo_ru}"),
                "Локальные коммерческие риски.",
            ),
        }
        item = local_map.get(category)
        return [item] if item else []

    if phase == "adjacent":
        return [
            (
                _clean_query(f"creator economy tools automation {category.replace('_', ' ')}"),
                "Смежный рынок Creator Economy.",
            ),
        ]

    if phase == "transferability":
        return [
            (
                _clean_query(
                    f"переносимость международных данных martech {geo_ru or 'Russia'}"
                ),
                "Оценка применимости международных данных к региону.",
            ),
        ]

    return []


def build_cascade_research_plan(
    inp: BusinessIdeaValidationInput,
) -> list[BusinessIdeaValidationResearchPlanItem]:
    """Full pipeline plan — engine runs all phases before verdict."""
    decomp = decompose_intake(inp)
    items: list[BusinessIdeaValidationResearchPlanItem] = []
    round_num = 1

    for category in CANONICAL_CATEGORIES:
        if category == "local_context" and not (decomp.geography or inp.location):
            continue
        base = queries_for_category(decomp, category)
        for phase in PIPELINE_PHASES:
            for query, rationale in _phase_queries(
                phase=phase,
                category=category,
                decomp=decomp,
                base_queries=base,
            ):
                if not query:
                    continue
                items.append(
                    BusinessIdeaValidationResearchPlanItem(
                        category=category,
                        query=query,
                        rationale=f"{_PHASE_LABELS.get(phase, phase)}: {rationale}",
                        round_number=round_num,
                        pipeline_phase=phase,
                    )
                )
                round_num = min(round_num + 1, 6)
    return items


def phases_completed(plan_items: list[BusinessIdeaValidationResearchPlanItem]) -> list[str]:
    seen: list[str] = []
    for item in plan_items:
        phase = item.pipeline_phase or "direct"
        if phase not in seen:
            seen.append(phase)
    return seen

"""Read-only marketing skill recommendations (Phase AI.234)."""

from __future__ import annotations

from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    MarketingSkillSuggestion,
    MarketingSkillType,
)


def build_skill_suggestions(
    intent: BusinessIntent,
    *,
    brief: CampaignBriefFields | None = None,
) -> list[MarketingSkillSuggestion]:
    suggestions: list[MarketingSkillSuggestion] = []
    has_audience = bool(brief and brief.target_audience) or bool(intent.industry)
    has_offer = bool(brief and brief.offer)

    if has_audience:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.SEGMENT_RESEARCH,
                label="Сбор информации о сегменте",
                safe_description="Структурируйте pains, desires и research questions перед оффером.",
            ),
        )

    if has_offer or intent.industry:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.MEANING_UNPACKING,
                label="Распаковка смыслов",
                safe_description="Свяжите боли аудитории с обещаниями и контраргументами.",
            ),
        )

    if has_offer and has_audience:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.OFFER_PACKAGING,
                label="Упаковка сильного оффера",
                safe_description="Соберите measurable result, mechanism и offer variants.",
            ),
        )
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.OFFER_JUSTIFICATION,
                label="Обоснование оффера",
                safe_description="Подготовьте business case, proof blocks и final CTA.",
            ),
        )

    if has_offer or intent.industry:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.WORDSTAT_RESEARCH,
                label="Проверка спроса (Wordstat skill)",
                safe_description="Skill с business-выводом; tool call только при create_tool_call=true.",
            ),
        )

    if intent.goal in {"lead_generation", "traffic", "promo", "sales"}:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.METRICA_ANALYSIS,
                label="Анализ трафика (Metrica skill)",
                safe_description="Skill с выводом по эффективности; tool call только явно.",
            ),
        )

    if has_offer:
        suggestions.append(
            MarketingSkillSuggestion(
                skill_type=MarketingSkillType.VISUAL_REPORT,
                label="Визуальный отчёт",
                safe_description="Creative direction + optional mock visual via tool call.",
            ),
        )

    return suggestions

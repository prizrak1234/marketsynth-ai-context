"""Read-only marketing tool suggestions (Phase AI.222)."""

from __future__ import annotations

from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    MarketingToolSuggestion,
    MarketingToolType,
)


def build_tool_suggestions(
    intent: BusinessIntent,
    *,
    brief: CampaignBriefFields | None = None,
) -> list[MarketingToolSuggestion]:
    suggestions: list[MarketingToolSuggestion] = []

    if intent.industry or (brief and brief.offer):
        suggestions.append(
            MarketingToolSuggestion(
                tool_type=MarketingToolType.WORDSTAT,
                label="Проверить спрос через Wordstat",
                safe_description=(
                    "Сравните спрос и конкуренцию по ключевым фразам перед запуском кампании."
                ),
            ),
        )

    if intent.goal in {"lead_generation", "traffic", "promo", "sales"}:
        suggestions.append(
            MarketingToolSuggestion(
                tool_type=MarketingToolType.METRICA,
                label="Проверить трафик через Metrica",
                safe_description=(
                    "Посмотрите визиты, пользователей и источники трафика на сайте."
                ),
            ),
        )

    if intent.goal in {"lead_generation", "promo", "brand", "content"}:
        suggestions.append(
            MarketingToolSuggestion(
                tool_type=MarketingToolType.IMAGE_GENERATION,
                label="Сделать визуал",
                safe_description="Сгенерируйте mock-креатив для превью кампании.",
            ),
        )

    return suggestions

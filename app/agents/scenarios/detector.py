"""Detect marketing orchestrator scenario from chat text and workflow (Phase AI.9)."""

from __future__ import annotations

from app.agents.scenarios.contracts import MarketingScenarioType
from app.schemas.contracts import CampaignWorkflowState

_SCENARIO_PHRASES: dict[MarketingScenarioType, tuple[str, ...]] = {
    MarketingScenarioType.TELEGRAM_CONTENT_MONTH: (
        "контент-план на месяц",
        "контент план на месяц",
        "план контента на месяц",
        "telegram content month",
        "content plan for a month",
        "monthly content plan",
        "контент на месяц",
    ),
    MarketingScenarioType.PRODUCT_ANNOUNCEMENT: (
        "новый продукт",
        "запускаем новый",
        "запуск продукта",
        "product launch",
        "product announcement",
        "launching a product",
        "анонс продукта",
        "релиз продукта",
    ),
    MarketingScenarioType.LEAD_MAGNET: (
        "лид-магнит",
        "лид магнит",
        "lead magnet",
        "lead-magnet",
        "чеклист",
        "checklist magnet",
    ),
    MarketingScenarioType.CAMPAIGN_REVIVAL: (
        "оживить кампанию",
        "оживим",
        "оживи ",
        "реактивировать",
        "campaign revival",
        "revive this campaign",
        "revive campaign",
        "перезапустить кампанию",
        "снова запустить",
    ),
    MarketingScenarioType.CONTENT_LAUNCH: (
        "контент-запуск",
        "content launch",
        "запуск контента",
        "launch campaign",
        "запустить кампанию",
        "создай план",
        "create a plan",
        "создать план",
    ),
}

_WORKFLOW_SCENARIO_HINTS: dict[str, MarketingScenarioType] = {
    CampaignWorkflowState.COMPLETED.value: MarketingScenarioType.CAMPAIGN_REVIVAL,
    CampaignWorkflowState.PLANNING.value: MarketingScenarioType.CONTENT_LAUNCH,
}


def detect_marketing_scenario(
    *,
    message: str,
    workflow_state: str = "",
) -> MarketingScenarioType | None:
    """Return the best-matching scenario or None when the request is generic/unknown."""
    normalized = " ".join((message or "").lower().split())
    if not normalized:
        return _workflow_only_hint(workflow_state)

    scores: dict[MarketingScenarioType, int] = {}
    for scenario_type, phrases in _SCENARIO_PHRASES.items():
        for phrase in phrases:
            if phrase in normalized:
                scores[scenario_type] = scores.get(scenario_type, 0) + len(phrase)

    if "telegram" in normalized and any(
        token in normalized for token in ("месяц", "month", "monthly", "контент-план", "content plan")
    ):
        scores[MarketingScenarioType.TELEGRAM_CONTENT_MONTH] = (
            scores.get(MarketingScenarioType.TELEGRAM_CONTENT_MONTH, 0) + 10
        )

    workflow_hint = _WORKFLOW_SCENARIO_HINTS.get(workflow_state.strip())
    if workflow_hint is not None and not scores:
        return workflow_hint

    if not scores:
        if any(
            token in normalized
            for token in (
                "что делать дальше",
                "what should we do next",
                "следующий шаг",
                "next step",
            )
        ):
            return None
        return None

    return max(scores.items(), key=lambda item: item[1])[0]


def _workflow_only_hint(workflow_state: str) -> MarketingScenarioType | None:
    return _WORKFLOW_SCENARIO_HINTS.get(workflow_state.strip())

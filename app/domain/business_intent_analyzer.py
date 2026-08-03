"""Rule-based business intent analyzer (Phase AI.178)."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.contracts import BusinessIntent

_INDUSTRY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "dental",
        (
            "стоматолог",
            "dental",
            "зубн",
            "имплант",
            "dentist",
            "клиник",
            "orthodont",
        ),
    ),
    (
        "restaurant",
        (
            "ресторан",
            "restaurant",
            "кафе",
            "cafe",
            "общепит",
            "кухн",
            "bistro",
            "food",
        ),
    ),
    (
        "expert",
        (
            "эксперт",
            "блог",
            "blogger",
            "личный бренд",
            "контент-машин",
            "контент машин",
            "expert",
            "influencer",
            "персональн",
        ),
    ),
    (
        "saas",
        (
            "saas",
            "telegram bot",
            "telegram-bot",
            "телеграм бот",
            "телеграм-бот",
            "software",
            "стартап",
            "startup",
            "приложен",
            "bot launch",
        ),
    ),
    (
        "local",
        (
            "локальн",
            "local",
            "салон",
            "услуг",
            "мастер",
            "сервис",
            "barber",
            "парикмах",
            "автосервис",
        ),
    ),
)

_GOAL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "lead_generation",
        (
            "лид",
            "lead",
            "заявк",
            "пациент",
            "клиент",
            "запись",
            "conversion",
        ),
    ),
    (
        "launch",
        (
            "запуск",
            "launch",
            "открыт",
            "новый",
            "open",
        ),
    ),
    (
        "content",
        (
            "контент",
            "content",
            "публикац",
            "блог",
            "editorial",
        ),
    ),
    (
        "promo",
        (
            "продвиж",
            "promo",
            "реклам",
            "маркетинг",
            "promotion",
        ),
    ),
)

_INDUSTRY_TO_BUSINESS_TYPE: dict[str, str] = {
    "dental": "clinic",
    "restaurant": "hospitality",
    "expert": "personal_brand",
    "saas": "software",
    "local": "local_service",
}

_INDUSTRY_DEFAULT_GOAL: dict[str, str] = {
    "dental": "lead_generation",
    "restaurant": "launch",
    "expert": "content",
    "saas": "launch",
    "local": "promo",
}

_INDUSTRY_TO_SCENARIO: dict[str, str] = {
    "dental": "dental_clinic_lead_gen",
    "restaurant": "restaurant_launch",
    "expert": "expert_blogger_content_machine",
    "saas": "telegram_bot_saas_launch",
    "local": "local_service_promo",
}

_CAMPAIGN_NAMES: dict[str, str] = {
    "dental_clinic_lead_gen": "Набор лидов для стоматологии",
    "restaurant_launch": "Запуск ресторана",
    "expert_blogger_content_machine": "Контент-машина для эксперта",
    "telegram_bot_saas_launch": "Запуск Telegram-бота / SaaS",
    "local_service_promo": "Продвижение локального бизнеса",
}


@dataclass(frozen=True, slots=True)
class IntentAnalysisResult:
    intent: BusinessIntent
    recommended_scenario: str
    recommended_campaign_name: str
    industry_keyword_score: int = 0
    goal_keyword_score: int = 0


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _score_keywords(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _best_match(
    text: str,
    rules: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[str | None, int]:
    best_key: str | None = None
    best_score = 0
    for key, keywords in rules:
        score = _score_keywords(text, keywords)
        if score > best_score:
            best_key = key
            best_score = score
    return best_key, best_score


def analyze_business_message(message: str) -> IntentAnalysisResult:
    """Parse user message into BusinessIntent without LLM."""
    normalized = _normalize(message)
    industry, industry_score = _best_match(normalized, _INDUSTRY_RULES)
    goal, goal_score = _best_match(normalized, _GOAL_RULES)

    if industry is None:
        industry = "local"
        industry_score = 0

    if goal is None:
        goal = _INDUSTRY_DEFAULT_GOAL.get(industry, "promo")
        goal_score = 0

    scenario_id = _INDUSTRY_TO_SCENARIO[industry]
    business_type = _INDUSTRY_TO_BUSINESS_TYPE.get(industry)
    campaign_type = goal

    confidence = min(1.0, 0.35 + industry_score * 0.2 + goal_score * 0.15)
    if industry_score == 0:
        confidence = min(confidence, 0.45)

    intent = BusinessIntent(
        goal=goal,
        industry=industry,
        business_type=business_type,
        campaign_type=campaign_type,
        confidence=round(confidence, 2),
        recommended_scenario=scenario_id,
    )
    campaign_name = _CAMPAIGN_NAMES.get(scenario_id, scenario_id.replace("_", " ").title())
    return IntentAnalysisResult(
        intent=intent,
        recommended_scenario=scenario_id,
        recommended_campaign_name=campaign_name,
        industry_keyword_score=industry_score,
        goal_keyword_score=goal_score,
    )


def campaign_name_for_scenario(scenario_id: str) -> str:
    return _CAMPAIGN_NAMES.get(scenario_id, scenario_id.replace("_", " ").title())

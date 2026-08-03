"""Campaign brief draft builder (Phase AI.210)."""

from __future__ import annotations

from app.domain.business_intent_analyzer import campaign_name_for_scenario
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import BusinessIntent, CampaignBriefFields

_GOAL_SUCCESS_METRICS: dict[str, str] = {
    "lead_generation": "Qualified leads or booked appointments",
    "launch": "Successful launch awareness and first conversions",
    "content": "Consistent content output and audience growth",
    "promo": "Increased local visibility and inbound requests",
}


def build_brief_draft(
    intent: BusinessIntent,
    *,
    scenario_id: str,
    message: str,
) -> CampaignBriefFields:
    """Seed in-memory brief draft from resolved intent — not persisted."""
    template = get_scenario(scenario_id)
    business_name = _extract_business_name(message)
    return CampaignBriefFields(
        business_name=business_name,
        industry=intent.industry,
        goal=intent.goal,
        offer=_default_offer_hint(scenario_id, template.name if template else scenario_id),
        target_audience=_default_audience_hint(intent.industry, scenario_id),
        success_metric=_GOAL_SUCCESS_METRICS.get(intent.goal or "", "Measurable campaign outcome"),
    )


def _extract_business_name(message: str) -> str | None:
    cleaned = message.strip()
    if len(cleaned) <= 3:
        return None
    return None


def _default_offer_hint(scenario_id: str, scenario_name: str) -> str | None:
    hints = {
        "dental_clinic_lead_gen": None,
        "restaurant_launch": None,
        "expert_blogger_content_machine": None,
        "telegram_bot_saas_launch": None,
        "local_service_promo": None,
    }
    _ = scenario_name
    return hints.get(scenario_id)


def _default_audience_hint(industry: str | None, scenario_id: str) -> str | None:
    if industry == "dental":
        return None
    if scenario_id == "restaurant_launch":
        return None
    return None


def merge_brief_answers(
    brief: CampaignBriefFields,
    answers: dict[str, str],
) -> CampaignBriefFields:
    """Apply user answers to brief draft fields."""
    data = brief.model_dump()
    list_fields = {"channels"}
    for field, value in answers.items():
        if field not in data:
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        if field in list_fields:
            data[field] = [part.strip() for part in cleaned.split(",") if part.strip()]
        else:
            data[field] = cleaned
    return CampaignBriefFields.model_validate(data)


def recommended_campaign_name_for_scenario(scenario_id: str) -> str:
    return campaign_name_for_scenario(scenario_id)

"""Scenario explanation and campaign preview builders (Phase AI.190–AI.191)."""

from __future__ import annotations

from app.domain.business_intent_analyzer import campaign_name_for_scenario
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import (
    BusinessIntent,
    BusinessOperatorCampaignPreview,
    ScenarioExplanation,
    ScenarioRecommendation,
)

_SCENARIO_LABELS: dict[str, str] = {
    "dental_clinic_lead_gen": "Dental Clinic Lead Gen",
    "restaurant_launch": "Restaurant Launch",
    "expert_blogger_content_machine": "Expert / Blogger Content Machine",
    "telegram_bot_saas_launch": "Telegram Bot / SaaS Launch",
    "local_service_promo": "Local Service Promo",
}


def scenario_display_name(scenario_id: str) -> str:
    template = get_scenario(scenario_id)
    if template is not None:
        return template.name
    return _SCENARIO_LABELS.get(scenario_id, scenario_id.replace("_", " ").title())


def build_scenario_explanation(
    intent: BusinessIntent,
    recommendation: ScenarioRecommendation,
    *,
    campaign_name: str,
) -> ScenarioExplanation:
    """Explain why a scenario was chosen and what the user must confirm."""
    scenario_id = recommendation.recommended_scenario
    template = get_scenario(scenario_id)
    scenario_name = scenario_display_name(scenario_id)

    industry_part = intent.industry or "general"
    goal_part = intent.goal.replace("_", " ")
    why = (
        f"Your {industry_part} business with goal '{goal_part}' matches "
        f"the {scenario_name} scenario."
    )
    if template is not None:
        why = (
            f"{why} It covers {len(template.required_specialists)} marketing specialists "
            f"for {template.industry.lower()}."
        )

    alt_labels = [
        scenario_display_name(alt_id) for alt_id in recommendation.alternative_scenarios
    ]
    specialists_count = len(template.required_specialists) if template else 0
    artifacts_count = len(template.expected_artifacts) if template else 0

    what_created = (
        f"A draft campaign '{campaign_name}' linked to scenario '{scenario_name}' "
        f"with {specialists_count} specialists and {artifacts_count} expected artifacts. "
        "Control Center opens next — no wizard or publishing starts automatically."
    )
    must_confirm = (
        "Confirm campaign creation. You will still start the scenario wizard and each "
        "action manually from the Action Center."
    )

    return ScenarioExplanation(
        why_this_scenario=why,
        alternatives=alt_labels,
        what_will_be_created=what_created,
        what_user_must_confirm=must_confirm,
    )


def build_campaign_preview(
    scenario_id: str,
    campaign_name: str | None = None,
) -> BusinessOperatorCampaignPreview | None:
    """Build read-only preview without creating DB objects."""
    template = get_scenario(scenario_id)
    if template is None:
        return None
    name = campaign_name or campaign_name_for_scenario(scenario_id)
    return BusinessOperatorCampaignPreview(
        campaign_name=name,
        goal=template.goal,
        scenario_id=scenario_id,
        scenario_name=template.name,
        specialists_count=len(template.required_specialists),
        expected_artifacts=list(template.expected_artifacts),
    )

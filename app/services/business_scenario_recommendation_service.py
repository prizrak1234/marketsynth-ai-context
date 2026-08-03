"""Scenario recommendation from business intent (Phase AI.179)."""

from __future__ import annotations

from app.domain.business_intent_analyzer import _INDUSTRY_TO_SCENARIO
from app.marketing.scenarios import SCENARIO_IDS, get_scenario
from app.schemas.contracts import BusinessIntent, ScenarioRecommendation

_GOAL_SCENARIO_HINTS: dict[str, tuple[str, ...]] = {
    "lead_generation": ("dental_clinic_lead_gen",),
    "launch": ("restaurant_launch", "telegram_bot_saas_launch"),
    "content": ("expert_blogger_content_machine",),
    "promo": ("local_service_promo", "restaurant_launch"),
}


def recommend_scenario(intent: BusinessIntent) -> ScenarioRecommendation:
    """Pick recommended scenario and alternatives from parsed intent."""
    primary = intent.recommended_scenario
    if primary is None and intent.industry:
        primary = _INDUSTRY_TO_SCENARIO.get(intent.industry)
    if primary is None:
        primary = "local_service_promo"

    template = get_scenario(primary)
    reason_parts: list[str] = []
    if intent.industry:
        reason_parts.append(f"industry={intent.industry}")
    if intent.goal:
        reason_parts.append(f"goal={intent.goal}")
    if template is not None:
        reason_parts.append(f"scenario={template.name}")
    reason = "Matched " + ", ".join(reason_parts) if reason_parts else f"Default scenario {primary}"

    alternatives: list[str] = []
    goal_hints = _GOAL_SCENARIO_HINTS.get(intent.goal, ())
    for scenario_id in goal_hints:
        if scenario_id != primary and scenario_id not in alternatives:
            alternatives.append(scenario_id)

    for scenario_id in SCENARIO_IDS:
        if scenario_id == primary or scenario_id in alternatives:
            continue
        other = get_scenario(scenario_id)
        if other is None:
            continue
        if intent.industry and intent.industry in other.industry.lower().replace(" ", "_"):
            alternatives.append(scenario_id)
        if len(alternatives) >= 2:
            break

    for scenario_id in SCENARIO_IDS:
        if scenario_id != primary and scenario_id not in alternatives:
            alternatives.append(scenario_id)
        if len(alternatives) >= 2:
            break

    confidence = min(1.0, max(intent.confidence, 0.5 if template else 0.35))
    return ScenarioRecommendation(
        recommended_scenario=primary,
        alternative_scenarios=alternatives[:2],
        reason=reason,
        confidence=round(confidence, 2),
    )

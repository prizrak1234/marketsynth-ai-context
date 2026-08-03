"""Scenario template registry (Phase AI.128)."""

from __future__ import annotations

from app.agents.marketer.marketing_specialist_registry import (
    get_marketing_specialist,
    list_marketing_specialists,
)
from app.schemas.contracts import (
    MarketingSpecialistTask,
    MarketingSpecialistType,
    ScenarioTemplate,
)

_REGISTERED_SPECIALISTS = frozenset(
    profile.specialist_type for profile in list_marketing_specialists()
)


def _tasks_for(
    specialists: tuple[MarketingSpecialistType, ...],
) -> list[MarketingSpecialistTask]:
    tasks: list[MarketingSpecialistTask] = []
    for specialist in specialists:
        profile = get_marketing_specialist(specialist)
        tasks.append(
            MarketingSpecialistTask(
                specialist=specialist,
                objective=profile.default_objective,
                expected_output=profile.default_expected_output,
            ),
        )
    return tasks


def _template(
    *,
    id: str,
    name: str,
    industry: str,
    goal: str,
    specialists: tuple[MarketingSpecialistType, ...],
    expected_artifacts: tuple[str, ...],
) -> ScenarioTemplate:
    tasks = _tasks_for(specialists)
    return ScenarioTemplate(
        id=id,
        name=name,
        industry=industry,
        goal=goal,
        required_specialists=list(specialists),
        default_plan_tasks=tasks,
        expected_artifacts=list(expected_artifacts),
    )


_SCENARIOS: dict[str, ScenarioTemplate] = {
    "restaurant_launch": _template(
        id="restaurant_launch",
        name="Restaurant Launch",
        industry="Food & hospitality",
        goal=(
            "Launch a new restaurant with positioning, content, offer, funnel, and social presence"
        ),
        specialists=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.FUNNEL_ARCHITECT,
            MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
            MarketingSpecialistType.SALES_COPYWRITER,
            MarketingSpecialistType.SMM_STRATEGIST,
        ),
        expected_artifacts=(
            "Positioning summary",
            "Content plan",
            "Offer strategy",
            "Funnel design",
            "Lead magnet concepts",
            "Sales page copy",
            "SMM strategy",
        ),
    ),
    "dental_clinic_lead_gen": _template(
        id="dental_clinic_lead_gen",
        name="Dental Clinic Lead Gen",
        industry="Healthcare / dental",
        goal=(
            "Generate qualified patient leads for a dental clinic with offer, funnel, "
            "and nurture flows"
        ),
        specialists=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.FUNNEL_ARCHITECT,
            MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
            MarketingSpecialistType.SALES_COPYWRITER,
            MarketingSpecialistType.EMAIL_DM_SPECIALIST,
            MarketingSpecialistType.CRO_SPECIALIST,
        ),
        expected_artifacts=(
            "Clinic offer strategy",
            "Patient acquisition funnel",
            "Lead magnet (checklist / quiz)",
            "Landing page copy",
            "Email / DM nurture sequence",
            "CRO recommendations",
        ),
    ),
    "expert_blogger_content_machine": _template(
        id="expert_blogger_content_machine",
        name="Expert / Blogger Content Machine",
        industry="Personal brand / media",
        goal="Build a sustainable content engine for an expert or blogger brand",
        specialists=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
            MarketingSpecialistType.CRITIC,
            MarketingSpecialistType.SMM_STRATEGIST,
            MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        ),
        expected_artifacts=(
            "Brand positioning",
            "Editorial content plan",
            "Channel-ready copy",
            "Quality critique",
            "SMM strategy",
            "Ad creative angles",
        ),
    ),
    "telegram_bot_saas_launch": _template(
        id="telegram_bot_saas_launch",
        name="Telegram Bot / SaaS Launch",
        industry="Software / bots",
        goal=(
            "Launch a Telegram bot or SaaS product with offer, funnel, sales copy, "
            "and paid creative"
        ),
        specialists=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.FUNNEL_ARCHITECT,
            MarketingSpecialistType.SALES_COPYWRITER,
            MarketingSpecialistType.EMAIL_DM_SPECIALIST,
            MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
            MarketingSpecialistType.CRO_SPECIALIST,
        ),
        expected_artifacts=(
            "Product offer strategy",
            "Launch funnel",
            "Sales page structure",
            "Onboarding / nurture sequences",
            "Paid ad creative matrix",
            "Conversion optimization notes",
        ),
    ),
    "local_service_promo": _template(
        id="local_service_promo",
        name="Local Service Promo",
        industry="Local services",
        goal=(
            "Promote a local service business with positioning, content, offer, "
            "and social outreach"
        ),
        specialists=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.SALES_COPYWRITER,
            MarketingSpecialistType.SMM_STRATEGIST,
        ),
        expected_artifacts=(
            "Local positioning",
            "Promo content plan",
            "Service offer framing",
            "Direct-response sales copy",
            "Local SMM strategy",
        ),
    ),
}

SCENARIO_IDS: tuple[str, ...] = tuple(_SCENARIOS.keys())


def list_scenarios() -> list[ScenarioTemplate]:
    return [_SCENARIOS[key] for key in SCENARIO_IDS]


def get_scenario(scenario_id: str) -> ScenarioTemplate | None:
    return _SCENARIOS.get(scenario_id)


def validate_scenario_specialists(template: ScenarioTemplate) -> None:
    for specialist in template.required_specialists:
        if specialist not in _REGISTERED_SPECIALISTS:
            raise ValueError(f"Unknown specialist in scenario {template.id}: {specialist}")
    task_specialists = [task.specialist for task in template.default_plan_tasks]
    if task_specialists != list(template.required_specialists):
        raise ValueError(f"Scenario {template.id} task order must match required_specialists")


for _scenario in _SCENARIOS.values():
    validate_scenario_specialists(_scenario)

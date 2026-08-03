"""Phase AI.128 — Scenario registry invariants."""

from __future__ import annotations

from app.marketing.scenarios import SCENARIO_IDS, get_scenario, list_scenarios


def test_scenario_registry_lists_five_product_templates() -> None:
    scenarios = list_scenarios()
    assert len(scenarios) == 5
    assert SCENARIO_IDS == (
        "restaurant_launch",
        "dental_clinic_lead_gen",
        "expert_blogger_content_machine",
        "telegram_bot_saas_launch",
        "local_service_promo",
    )
    for scenario_id in SCENARIO_IDS:
        template = get_scenario(scenario_id)
        assert template is not None
        assert template.id == scenario_id
        assert template.name
        assert template.industry
        assert template.goal
        assert template.expected_artifacts

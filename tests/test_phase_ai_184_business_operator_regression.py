"""Phase AI.184 — General Business Operator regression."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project

_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "Мне нужны лиды для стоматологии",
        "dental_clinic_lead_gen",
        "Набор лидов для стоматологии",
    ),
    (
        "Запуск нового ресторана",
        "restaurant_launch",
        "Запуск ресторана",
    ),
    (
        "Нужна контент-машина для эксперта блогера",
        "expert_blogger_content_machine",
        "Контент-машина для эксперта",
    ),
    (
        "Запуск telegram bot saas продукта",
        "telegram_bot_saas_launch",
        "Запуск Telegram-бота / SaaS",
    ),
    (
        "Продвижение локального сервиса в городе",
        "local_service_promo",
        "Продвижение локального бизнеса",
    ),
)


@pytest.mark.parametrize(
    ("message", "expected_scenario", "expected_campaign_name"),
    _CASES,
)
def test_analyze_recommends_expected_scenario(
    client: TestClient,
    auth_headers: dict[str, str],
    message: str,
    expected_scenario: str,
    expected_campaign_name: str,
) -> None:
    project_id = create_project(client, auth_headers, "AI.184 operator analyze")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": message},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommended_scenario"] == expected_scenario
    assert body["recommended_campaign_name"] == expected_campaign_name
    assert body["intent"]["recommended_scenario"] == expected_scenario
    assert body["recommendation"]["recommended_scenario"] == expected_scenario
    assert body["recommendation"]["confidence"] >= 0.35
    assert body["recommendation"]["reason"]


def test_create_campaign_stores_source_business_intent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from tests.helpers.business_operator_helpers import (
        analyze_operator,
        complete_and_confirm_brief,
        create_operator_campaign,
    )

    project_id = create_project(client, auth_headers, "AI.184 operator create")
    message = "Мне нужны лиды для стоматологии"
    analyzed = analyze_operator(client, auth_headers, project_id, message)
    brief_id = complete_and_confirm_brief(
        client,
        auth_headers,
        project_id,
        analyzed,
        extra_answers={
            "offer": "Dental implants and hygiene packages",
            "target_audience": "Adults 30-55 in the city",
        },
    )
    body = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    campaign = body["campaign"]
    assert campaign["scenario_id"] == "dental_clinic_lead_gen"
    assert campaign["name"] == "Набор лидов для стоматологии"
    intent_meta = campaign["metadata"]["source_business_intent"]
    assert intent_meta["industry"] == "dental"
    assert intent_meta["goal"] == "lead_generation"
    assert intent_meta["recommended_scenario"] == "dental_clinic_lead_gen"
    assert body["control_center"]["campaign"]["id"] == campaign["id"]
    assert body["control_center"]["primary_action"] is not None


def test_analyze_requires_non_empty_message(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.184 operator empty")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422

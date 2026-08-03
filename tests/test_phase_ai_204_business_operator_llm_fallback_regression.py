"""Phase AI.204 — Business Operator LLM fallback regression."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.schemas.contracts import BusinessOperatorLLMIntent
from app.services.business_operator_llm_service import BusinessOperatorLLMService
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


@pytest.fixture
def enable_llm_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def disable_llm_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_high_confidence_dental_does_not_use_llm(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(_self, _message: str):
        raise AssertionError("LLM must not be called for high-confidence rule match")

    monkeypatch.setattr(BusinessOperatorLLMService, "classify_intent", fail_if_called)
    project_id = create_project(client, auth_headers, "AI.204 dental no llm")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "Мне нужны лиды для стоматологии"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rule_based"
    assert body["llm_used"] is False
    assert body["confidence_gate_passed"] is True
    assert body["confidence_before"] == body["confidence_after"]


def test_vague_message_uses_llm_when_flag_on(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.204 vague llm on")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "llm_fallback"
    assert body["llm_used"] is True
    assert body["llm_provider"] == "mock"
    assert body["confidence_before"] < body["confidence_after"]
    assert body["confidence_gate_passed"] is True
    assert body["preview"] is not None
    assert body["recommended_scenario"] == "local_service_promo"


def test_vague_message_clarification_when_flag_off(
    client: TestClient,
    auth_headers: dict[str, str],
    disable_llm_fallback: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.204 vague flag off")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "clarification"
    assert body["llm_used"] is False
    assert body["confidence_gate_passed"] is False
    assert body["clarification_questions"]
    assert body["preview"] is None


def test_invalid_llm_scenario_falls_back_to_clarification(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = BusinessOperatorLLMIntent(
        goal="lead_generation",
        industry="dental",
        suggested_scenario="not_a_real_scenario",
        confidence=0.95,
        reasoning_summary="invalid scenario test",
        missing_fields=[],
    )

    async def return_invalid(_self, _message: str):
        return invalid, "mock", "mock-model"

    monkeypatch.setattr(BusinessOperatorLLMService, "classify_intent", return_invalid)
    project_id = create_project(client, auth_headers, "AI.204 invalid llm")
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "clarification"
    assert body["llm_used"] is False
    assert body["confidence_gate_passed"] is False
    assert body["clarification_questions"]


def test_analyze_does_not_auto_create_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.204 no auto create")
    before = client.get(
        f"/projects/{project_id}/business-campaigns",
        headers=auth_headers,
    )
    count_before = len(before.json())

    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    after = client.get(
        f"/projects/{project_id}/business-campaigns",
        headers=auth_headers,
    )
    assert len(after.json()) == count_before


def test_audit_fields_safe_on_analyze(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.204 audit safe")
    message = "хочу клиентов"
    response = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": message},
        headers=auth_headers,
    )
    body = response.json()
    assert body["intent_audit_id"]
    assert len(body["message_preview"]) <= 80
    assert body["message_preview"] == message
    assert "raw_completion" not in body
    assert "raw_prompt" not in body
    assert body["llm_provider"] == "mock"
    assert body["llm_model"]


def test_mock_llm_classify_is_deterministic() -> None:
    service = BusinessOperatorLLMService()

    async def run(message: str):
        return await service.classify_intent(message)

    import asyncio

    first = asyncio.run(run("хочу клиентов"))
    second = asyncio.run(run("хочу клиентов"))
    assert first == second
    assert first[0] is not None
    assert first[0].confidence == 0.72


def test_low_confidence_create_still_blocked_without_gate(
    client: TestClient,
    auth_headers: dict[str, str],
    disable_llm_fallback: None,
) -> None:
    from uuid import uuid4

    project_id = create_project(client, auth_headers, "AI.204 create blocked")
    response = client.post(
        f"/projects/{project_id}/business-operator/create-campaign",
        json={"message": "хочу клиентов", "brief_id": str(uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_alternatives_still_present_with_llm_fallback(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_llm_fallback: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.204 alternatives")
    body = client.post(
        f"/projects/{project_id}/business-operator/analyze",
        json={"message": "хочу клиентов"},
        headers=auth_headers,
    ).json()
    assert body["recommendation"]["alternative_scenarios"]
    assert body["explanation"]["alternatives"]

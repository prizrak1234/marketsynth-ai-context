"""Phase AI.235 — Marketing skills layer freeze regression."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.marketing.skills.registry import get_marketing_skill_registry
from fastapi.testclient import TestClient
from tests.helpers.business_operator_helpers import (
    analyze_operator,
    complete_and_confirm_brief,
    create_operator_campaign,
)
from tests.helpers.v2_specialist_execution_helpers import create_project


@pytest.fixture
def enable_marketing_skills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKETING_SKILLS_ENABLED", "true")
    monkeypatch.setenv("MARKETING_DATA_TOOLS_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def disable_marketing_skills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKETING_SKILLS_ENABLED", "false")
    monkeypatch.setenv("MARKETING_SKILLS_MOCK_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()


def test_skill_registry_lists_seven_skills() -> None:
    definitions = get_marketing_skill_registry().list_definitions()
    assert len(definitions) == 7
    types = {item.skill_type.value for item in definitions}
    assert types == {
        "segment_research",
        "meaning_unpacking",
        "offer_packaging",
        "offer_justification",
        "wordstat_research",
        "metrica_analysis",
        "visual_report",
    }


def test_segment_research_skill_run(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 segment")
    response = client.post(
        f"/projects/{project_id}/marketing-skills/segment_research/runs",
        json={
            "input_payload": {
                "industry": "dental",
                "target_audience": "Adults 30-55",
                "geography": "Moscow",
                "offer": "Dental implants package",
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    output = body["output_payload"]
    assert output["soc_dem"]
    assert output["pains"]
    assert output["research_questions"]
    assert body["used_tool_call_ids"] == []


def test_meaning_unpacking_and_offer_skills(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 offer chain")
    payload = {
        "input_payload": {
            "offer": "Premium dental implants",
            "target_audience": "Adults 30-55",
            "industry": "dental",
        },
    }
    for skill in ("meaning_unpacking", "offer_packaging", "offer_justification"):
        response = client.post(
            f"/projects/{project_id}/marketing-skills/{skill}/runs",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "succeeded"


def test_wordstat_skill_without_tool_call(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 wordstat skill")
    response = client.post(
        f"/projects/{project_id}/marketing-skills/wordstat_research/runs",
        json={
            "input_payload": {
                "query": "стоматология",
                "create_tool_call": False,
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["output_payload"]["business_conclusion"]
    assert body["used_tool_call_ids"] == []


def test_data_skills_create_tool_calls_when_explicit(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 data skills tools")
    wordstat = client.post(
        f"/projects/{project_id}/marketing-skills/wordstat_research/runs",
        json={
            "input_payload": {
                "query": "dental leads",
                "create_tool_call": True,
            },
        },
        headers=auth_headers,
    )
    assert wordstat.status_code == 201
    wordstat_body = wordstat.json()
    assert wordstat_body["used_tool_call_ids"]
    assert wordstat_body["output_payload"]["wordstat_summary"]["provider"] == "mock"

    metrica = client.post(
        f"/projects/{project_id}/marketing-skills/metrica_analysis/runs",
        json={"input_payload": {"create_tool_call": True, "industry": "dental"}},
        headers=auth_headers,
    )
    assert metrica.status_code == 201
    assert metrica.json()["used_tool_call_ids"]


def test_rejects_secret_keys_in_skill_input(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 skill secrets")
    response = client.post(
        f"/projects/{project_id}/marketing-skills/segment_research/runs",
        json={"input_payload": {"target_audience": "test", "api_key": "sk-secret"}},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_permissions_block_when_skills_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
    disable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 disabled")
    response = client.post(
        f"/projects/{project_id}/marketing-skills/segment_research/runs",
        json={"input_payload": {"target_audience": "test"}},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_list_and_get_skill_runs(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 list runs")
    created = client.post(
        f"/projects/{project_id}/marketing-skills/visual_report/runs",
        json={"input_payload": {"offer": "Dental promo banner", "industry": "dental"}},
        headers=auth_headers,
    )
    run_id = created.json()["id"]

    listed = client.get(f"/projects/{project_id}/marketing-skills/runs", headers=auth_headers)
    assert listed.status_code == 200
    assert any(row["id"] == run_id for row in listed.json())

    fetched = client.get(
        f"/projects/{project_id}/marketing-skills/runs/{run_id}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200


def test_control_center_includes_skill_suggestions(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 cc skills")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
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
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    campaign_id = created["campaign"]["id"]

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    suggestions = center.json().get("skill_suggestions") or []
    assert suggestions
    first = suggestions[0]
    assert first.get("reason")
    assert first.get("label")
    skill_types = {item["skill_type"] for item in suggestions}
    assert "segment_research" in skill_types
    assert "offer_packaging" in skill_types


def test_skill_suggestions_do_not_auto_run(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 no auto run")
    analyzed = analyze_operator(
        client,
        auth_headers,
        project_id,
        "Мне нужны лиды для стоматологии",
    )
    assert analyzed.get("tool_suggestions")

    listed = client.get(f"/projects/{project_id}/marketing-skills/runs", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_get_unknown_skill_run_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id = create_project(client, auth_headers, "AI.235 not found")
    response = client.get(
        f"/projects/{project_id}/marketing-skills/runs/{uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404

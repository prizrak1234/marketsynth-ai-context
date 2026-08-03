"""Phase AI.254 — Campaign supervisor regression."""

from __future__ import annotations

import pytest
from app.schemas.contracts import CampaignActionType, CampaignSupervisorSeverity
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


def _operator_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
    label: str,
    *,
    extra_answers: dict[str, str] | None = None,
) -> tuple[str, str]:
    project_id = create_project(client, auth_headers, label)
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
            "success_metric": "Qualified dental leads per month",
            **(extra_answers or {}),
        },
    )
    created = create_operator_campaign(client, auth_headers, project_id, analyzed, brief_id)
    return project_id, created["campaign"]["id"]


def test_supervisor_report_detects_missing_brief_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.254 sparse brief")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Campaign without confirmed brief",
            "goal": "Dental leads",
            "scenario_id": "dental_clinic_lead_gen",
            "metadata": {
                "source_business_intent": {
                    "goal": "lead_generation",
                    "industry": "dental",
                    "confidence": 0.7,
                    "recommended_scenario": "dental_clinic_lead_gen",
                },
            },
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert "offer" in body["missing_inputs"]
    assert "target_audience" in body["missing_inputs"]
    assert "success_metric" in body["missing_inputs"]
    assert body["health_score"] < 100
    categories = {item["category"] for item in body["findings"]}
    assert "brief" in categories


def test_supervisor_report_flags_missing_lead_gen_skills(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_marketing_skills: None,
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.254 skills")

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert report.status_code == 200
    body = report.json()
    titles = {item["title"] for item in body["findings"]}
    assert "Wordstat research recommended for lead generation" in titles
    action_types = {item["recommended_action_type"] for item in body["findings"] if item["recommended_action_type"]}
    assert CampaignActionType.RUN_WORDSTAT_RESEARCH.value in action_types
    assert CampaignActionType.RUN_SEGMENT_RESEARCH.value in action_types


def test_supervisor_report_contradiction_for_lead_metric_mismatch(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(
        client,
        auth_headers,
        "AI.254 contradiction",
        extra_answers={"success_metric": "Brand awareness and social likes"},
    )

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert report.status_code == 200
    body = report.json()
    assert body["contradictions"]
    assert any(item["title"] == "Success metric mismatch" for item in body["findings"])


def test_control_center_includes_supervisor_summary(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.254 cc summary")

    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert "supervisor_health_score" in body
    assert body["supervisor_findings_count"] >= 1
    assert isinstance(body.get("top_findings"), list)
    assert len(body["top_findings"]) <= 5


def test_supervisor_report_is_read_only(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.254 no side effects")

    before = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}",
        headers=auth_headers,
    )
    assert before.status_code == 200
    before_updated_at = before.json()["updated_at"]

    first = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    second = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["health_score"] == second.json()["health_score"]

    runs = client.get(
        f"/projects/{project_id}/marketing-skills/runs",
        params={"campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert runs.status_code == 200
    assert runs.json() == []

    after = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}",
        headers=auth_headers,
    )
    assert after.json()["updated_at"] == before_updated_at


def test_supervisor_report_safe_metadata_only(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.254 safe metadata")

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    assert report.status_code == 200
    serialized = str(report.json())
    assert "output_payload" not in serialized
    assert "wordstat_summary" not in serialized
    assert "api_key" not in serialized


def test_supervisor_finding_severity_ordering(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, campaign_id = _operator_campaign(client, auth_headers, "AI.254 severity order")

    report = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/supervisor-report",
        headers=auth_headers,
    )
    findings = report.json()["findings"]
    severities = [CampaignSupervisorSeverity(item["severity"]) for item in findings]
    order = {"critical": 0, "warning": 1, "info": 2}
    assert severities == sorted(severities, key=lambda item: order[item.value])

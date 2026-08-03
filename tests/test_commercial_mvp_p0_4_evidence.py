"""Commercial MVP P0.4 — Evidence domain API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.llm import LLMRequestTable
from app.db.models.evidence import InvestigationEvidenceTable
from app.services.evidence_service import EvidenceService


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _project(client: TestClient, headers: dict[str, str], name: str = "P0.4 Ev") -> str:
    r = client.post("/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def _brief_body() -> dict:
    return {
        "language": "ru",
        "project_basics": {
            "project_name": "Clinic",
            "idea_description": "Leads",
            "business_type": "local_business",
            "project_stage": "preparing_launch",
            "geography": "Moscow",
            "preferred_language": "ru",
        },
        "product": {
            "product_or_service": "Service",
            "customer_problem": "Pain",
            "value_proposition": "Value",
            "price": {"mode": "unknown"},
            "delivery_model": "clinic",
            "differentiators": "x",
            "limitations": "y",
        },
        "market": {
            "target_market": "Adults",
            "geography": "Moscow",
            "known_competitors": "",
            "competitor_urls": "",
            "market_assumptions": "a",
            "demand_evidence": "d",
            "seasonality": "",
            "restrictions": "",
        },
        "audience": {
            "business_model": "b2c",
            "segments": [],
            "decision_maker": "Patient",
            "buyer_user_distinction": "same",
            "geography": "Moscow",
            "pains": "p",
            "objections": "o",
            "current_research": "r",
        },
        "economics": {
            "launch_budget": {"mode": "unknown"},
            "monthly_marketing_budget": {"mode": "unknown"},
            "target_revenue": {"mode": "unknown"},
            "payback_period": "",
            "average_order_value": {"mode": "unknown"},
            "gross_margin": "",
            "team_size": "",
            "internal_resources": "",
            "launch_deadline": "",
            "critical_constraints": "",
        },
        "materials_summary": {"website_url": "", "social_profiles": "", "items": []},
        "assumptions": ["a"],
        "missing_data": [],
        "readiness_status": "conditionally_ready",
        "readiness_reasons": ["pending"],
    }


def _setup_inv_and_source(
    client: TestClient, headers: dict[str, str], project_id: str
) -> tuple[str, str]:
    brief = client.post(
        f"/projects/{project_id}/briefs", json=_brief_body(), headers=headers
    ).json()
    submitted = client.post(
        f"/projects/{project_id}/briefs/{brief['id']}/submit", headers=headers
    ).json()
    inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": submitted["id"],
            "project_brief_version": submitted["version"],
            "input_fingerprint": submitted["input_fingerprint"],
        },
        headers=headers,
    ).json()
    src = client.post(
        f"/projects/{project_id}/sources",
        json={
            "source_type": "website",
            "provenance_type": "secondary",
            "title": "Competitor prices",
            "url": "https://example.com/prices",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=headers,
    ).json()
    return inv["id"], src["id"]


def test_create_review_accept_and_no_verdict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)

    # reject non-atomic / verdict-like
    bad = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Рынок перспективный и поэтому проект стоит запускать.",
            "evidence_type": "observed_fact",
            "source_links": [{"source_id": src_id, "stance": "supports"}],
        },
        headers=auth_headers,
    )
    assert bad.status_code == 409
    assert "non_atomic_claim" in _err(bad)

    # reject missing source for non-missing
    no_src = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Средняя цена услуги у конкурентов 8000–12000 рублей.",
            "evidence_type": "comparison",
            "assessment_state": "unverified",
            "source_links": [],
        },
        headers=auth_headers,
    )
    assert no_src.status_code == 409
    assert "missing_source" in _err(no_src)

    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Средняя цена услуги у пяти зарегистрированных конкурентов 8000–12000 рублей.",
            "evidence_type": "comparison",
            "investigation_area": "competitor_analysis",
            "materiality": "critical",
            "source_links": [
                {
                    "source_id": src_id,
                    "stance": "supports",
                    "locator_type": "page",
                    "locator_value": "1",
                    "excerpt": "from 8000 to 12000",
                }
            ],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    ev = created.json()
    assert ev["lifecycle_status"] == "draft"
    assert ev["assessment_state"] == "unverified"
    assert ev["confidence_level"] == "unknown"
    assert len(ev["source_links"]) == 1
    assert ev["source_links"][0]["stance"] == "supports"

    reviewed = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}/submit-review",
        headers=auth_headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["lifecycle_status"] == "under_review"

    accepted = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}/accept",
        headers=auth_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["lifecycle_status"] == "accepted"
    assert accepted.json()["assessment_state"] == "confirmed"

    # immutable
    patch = client.patch(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}",
        json={"claim": "Changed claim must fail"},
        headers=auth_headers,
    )
    assert patch.status_code == 409

    summary = client.get(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/summary",
        headers=auth_headers,
    )
    assert summary.status_code == 200
    assert summary.json()["accepted_count"] >= 1
    assert summary.json()["creates_business_verdict"] is False
    assert summary.json()["verdict_readiness_contribution"] in (
        "sufficient",
        "partial",
        "blocked",
    )

    assert EvidenceService.creates_business_verdict() is False
    assert EvidenceService.completes_investigation() is False
    assert EvidenceService.creates_agent_run() is False


def test_missing_evidence_and_conflict_supersede(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.4 miss")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)

    missing = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Нет подтверждённых данных о сезонности спроса.",
            "evidence_type": "absence_signal",
            "assessment_state": "missing",
            "materiality": "critical",
            "why_it_matters": "Блокирует оценку demand.",
            "source_links": [],
        },
        headers=auth_headers,
    )
    assert missing.status_code == 201, missing.text
    assert missing.json()["assessment_state"] == "missing"

    # second source for contradiction
    src2 = client.post(
        f"/projects/{project_id}/sources",
        json={
            "source_type": "market_report",
            "title": "Alt report",
            "url": "https://example.com/alt",
            "capabilities": ["pdf", "text"],
            "attach_to_investigation_id": inv_id,
        },
        headers=auth_headers,
    ).json()

    conflicting = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Источники дают противоречивые оценки объёма рынка.",
            "evidence_type": "comparison",
            "assessment_state": "conflicting",
            "materiality": "critical",
            "source_links": [
                {"source_id": src_id, "stance": "supports"},
                {"source_id": src2["id"], "stance": "contradicts"},
            ],
        },
        headers=auth_headers,
    )
    assert conflicting.status_code == 201, conflicting.text
    assert len(conflicting.json()["source_links"]) == 2

    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{conflicting.json()['id']}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{conflicting.json()['id']}/accept",
        headers=auth_headers,
    )

    new = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{conflicting.json()['id']}/supersede",
        json={
            "claim": "Источники дают противоречивые оценки объёма рынка за 2025 год.",
            "evidence_type": "comparison",
            "assessment_state": "conflicting",
            "materiality": "critical",
            "source_links": [
                {"source_id": src_id, "stance": "supports"},
                {"source_id": src2["id"], "stance": "contradicts"},
            ],
        },
        headers=auth_headers,
    )
    assert new.status_code == 201, new.text
    assert new.json()["version"] == 2

    summary = client.get(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/summary",
        headers=auth_headers,
    ).json()
    assert summary["missing_critical_claims"] >= 1
    assert summary["verdict_readiness_contribution"] == "blocked"


def test_owner_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.4 iso")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)
    ev = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "География исследования ограничена Москвой.",
            "evidence_type": "constraint",
            "source_links": [{"source_id": src_id, "stance": "supports"}],
        },
        headers=auth_headers,
    ).json()
    other = client.get(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}",
        headers=other_auth_headers,
    )
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_no_agent_llm_from_evidence(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project(client, auth_headers, "P0.4 side")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)
    before_runs = (
        await db_session.execute(select(func.count()).select_from(AgentRunTable))
    ).scalar_one()
    before_llm = (
        await db_session.execute(select(func.count()).select_from(LLMRequestTable))
    ).scalar_one()
    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Один конкурент публикует прайс на сайте.",
            "evidence_type": "observed_fact",
            "source_links": [{"source_id": src_id, "stance": "supports"}],
        },
        headers=auth_headers,
    )
    after_runs = (
        await db_session.execute(select(func.count()).select_from(AgentRunTable))
    ).scalar_one()
    after_llm = (
        await db_session.execute(select(func.count()).select_from(LLMRequestTable))
    ).scalar_one()
    assert after_runs == before_runs
    assert after_llm == before_llm
    rows = await db_session.execute(select(InvestigationEvidenceTable))
    assert len(list(rows.scalars().all())) >= 1

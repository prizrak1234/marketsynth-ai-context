"""Commercial MVP P0.6 — MarketingStrategy domain API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_strategy import MarketingStrategyTable


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _project(client: TestClient, headers: dict[str, str], name: str = "P0.6 MS") -> str:
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


def _setup_inv(client: TestClient, headers: dict[str, str], project_id: str) -> tuple[str, str]:
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
            "title": "Market",
            "url": "https://example.com/m",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=headers,
    ).json()
    return inv["id"], src["id"]


def _accept_ev(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    inv_id: str,
    src_id: str,
    claim: str,
    area: str,
) -> dict:
    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": claim,
            "evidence_type": "observed_fact",
            "investigation_area": area,
            "materiality": "critical",
            "source_links": [
                {
                    "source_id": src_id,
                    "stance": "supports",
                    "locator_type": "page",
                    "locator_value": "1",
                    "excerpt": claim[:80],
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    ev = created.json()
    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}/submit-review",
        headers=headers,
    )
    accepted = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200
    return accepted.json()


def _approve_conditional_verdict(
    client: TestClient, headers: dict[str, str], project_id: str, inv_id: str, src_id: str
) -> dict:
    m = _accept_ev(
        client,
        headers,
        project_id,
        inv_id,
        src_id,
        "Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
        "market_research",
    )
    e = _accept_ev(
        client,
        headers,
        project_id,
        inv_id,
        src_id,
        "Средний чек по прайсу клиники составляет 9000 рублей.",
        "economics",
    )
    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts",
        json={
            "verdict_type": "conditional_go",
            "confidence_level": "medium",
            "executive_conclusion": "Условный GO.",
            "executive_rationale": "Есть Evidence, есть условия.",
            "primary_business_implication": "Strategy possible after conditions.",
            "recommended_next_action": "Validate CAC.",
            "evidence_links": [
                {"evidence_id": m["id"], "evidence_version": m["version"], "role": "supports"},
                {
                    "evidence_id": e["id"],
                    "evidence_version": e["version"],
                    "role": "condition_basis",
                },
            ],
            "conditions": [
                {
                    "id": "c1",
                    "title": "Подтвердить CAC",
                    "required_action": "Собрать CAC Evidence",
                    "owner_role": "owner",
                    "success_criterion": "CAC confirmed",
                    "evidence_required": True,
                    "consequence_if_unmet": "Block planning",
                    "status": "open",
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    client.post(f"/projects/{project_id}/business-verdicts/{vid}/submit-review", headers=headers)
    approved = client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/approve", headers=headers
    )
    assert approved.status_code == 200
    return approved.json()


def test_build_draft_from_conditional_go_and_firewall(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    inv_id, src_id = _setup_inv(client, auth_headers, project_id)
    verdict = _approve_conditional_verdict(client, auth_headers, project_id, inv_id, src_id)

    draft = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": verdict["id"]},
        headers=auth_headers,
    )
    assert draft.status_code == 201, draft.text
    body = draft.json()
    assert body["lifecycle_status"] == "draft"
    assert body["business_verdict_id"] == verdict["id"]
    assert body["business_verdict_version"] == verdict["version"]
    assert body["is_marketing_plan"] is False
    assert body["creates_marketing_plan"] is False
    assert body["creates_campaign"] is False
    assert body["creates_agent_run"] is False
    assert body["handoff_status"] == "not_started"
    assert any(c["verdict_condition_id"] == "c1" for c in body["verdict_conditions"])
    assert body["readiness_status"] in ("conditionally_ready", "ready_for_planning", "not_ready")

    client.post(
        f"/projects/{project_id}/marketing-strategies/{body['id']}/submit-review",
        headers=auth_headers,
    )
    approved = client.post(
        f"/projects/{project_id}/marketing-strategies/{body['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["creates_marketing_plan"] is False

    patched = client.patch(
        f"/projects/{project_id}/marketing-strategies/{body['id']}",
        json={"title": "hack"},
        headers=auth_headers,
    )
    assert patched.status_code == 409


def test_blocks_nogo_and_draft_verdict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "NOGO")
    inv_id, src_id = _setup_inv(client, auth_headers, project_id)
    ev = _accept_ev(
        client,
        auth_headers,
        project_id,
        inv_id,
        src_id,
        "Конкуренты демпингуют цену ниже себестоимости по открытым прайсам.",
        "economics",
    )
    nogo = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts",
        json={
            "verdict_type": "no_go",
            "confidence_level": "high",
            "executive_conclusion": "NO_GO.",
            "executive_rationale": "Risk.",
            "primary_business_implication": "Pivot.",
            "recommended_next_action": "Pivot.",
            "evidence_links": [
                {"evidence_id": ev["id"], "evidence_version": ev["version"], "role": "contradicts"}
            ],
            "critical_risks": [
                {
                    "title": "Loss",
                    "description": "Structural loss",
                    "severity": "critical",
                    "probability": "high",
                    "business_consequence": "Losses",
                    "verdict_sensitivity": "verdict_changing",
                }
            ],
        },
        headers=auth_headers,
    )
    assert nogo.status_code == 201
    vid = nogo.json()["id"]
    client.post(f"/projects/{project_id}/business-verdicts/{vid}/submit-review", headers=auth_headers)
    client.post(f"/projects/{project_id}/business-verdicts/{vid}/approve", headers=auth_headers)

    blocked = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": vid},
        headers=auth_headers,
    )
    assert blocked.status_code == 409
    assert "verdict_type_not_eligible" in _err(blocked)

    # draft insufficiency blocks
    draft_v = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts/build-draft",
        headers=auth_headers,
    )
    assert draft_v.status_code == 201
    blocked2 = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": draft_v.json()["id"]},
        headers=auth_headers,
    )
    assert blocked2.status_code == 409
    assert "verdict_not_approved" in _err(blocked2)


@pytest.mark.asyncio
async def test_strategy_approve_creates_no_plan_agent_llm(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project(client, auth_headers, "FW")
    inv_id, src_id = _setup_inv(client, auth_headers, project_id)
    verdict = _approve_conditional_verdict(client, auth_headers, project_id, inv_id, src_id)
    draft = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": verdict["id"]},
        headers=auth_headers,
    )
    assert draft.status_code == 201
    sid = draft.json()["id"]
    client.post(
        f"/projects/{project_id}/marketing-strategies/{sid}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/marketing-strategies/{sid}/approve",
        headers=auth_headers,
    )

    plans = await db_session.scalar(select(func.count()).select_from(MarketingPlanTable))
    runs = await db_session.scalar(select(func.count()).select_from(AgentRunTable))
    llms = await db_session.scalar(select(func.count()).select_from(LLMRequestTable))
    strategies = await db_session.scalar(
        select(func.count()).select_from(MarketingStrategyTable)
    )
    assert strategies and strategies >= 1
    assert plans == 0
    assert runs == 0
    assert llms == 0

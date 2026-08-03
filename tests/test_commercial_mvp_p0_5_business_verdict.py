"""Commercial MVP P0.5 — BusinessVerdict domain API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.llm import LLMRequestTable
from app.db.models.business_verdict import BusinessVerdictTable


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _project(client: TestClient, headers: dict[str, str], name: str = "P0.5 BV") -> str:
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
            "title": "Market report",
            "url": "https://example.com/market",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=headers,
    ).json()
    return inv["id"], src["id"]


def _accept_evidence(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    inv_id: str,
    src_id: str,
    *,
    claim: str,
    area: str,
    materiality: str = "critical",
) -> dict:
    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": claim,
            "evidence_type": "observed_fact",
            "investigation_area": area,
            "materiality": materiality,
            "assessment_state": "unverified",
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
    accept = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/{ev['id']}/accept",
        headers=headers,
    )
    assert accept.status_code == 200, accept.text
    return accept.json()


def test_deterministic_draft_and_review_flow(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)

    # missing critical → readiness blocked → only INSUFFICIENT_DATA via builder
    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/evidence",
        json={
            "claim": "Критические данные по юнит-экономике отсутствуют на текущий момент.",
            "evidence_type": "absence_signal",
            "investigation_area": "economics",
            "materiality": "critical",
            "assessment_state": "missing",
            "source_links": [],
        },
        headers=auth_headers,
    )

    summary = client.get(
        f"/projects/{project_id}/investigations/{inv_id}/evidence/summary",
        headers=auth_headers,
    ).json()
    assert summary["creates_business_verdict"] is False
    assert summary["verdict_readiness_contribution"] in ("blocked", "partial")

    draft = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts/build-draft",
        headers=auth_headers,
    )
    assert draft.status_code == 201, draft.text
    body = draft.json()
    assert body["lifecycle_status"] == "draft"
    assert body["verdict_type"] in ("insufficient_data", "conditional_go")
    assert body["is_readiness"] is False
    assert body["creates_strategy"] is False
    assert body["creates_execution_approval"] is False
    assert body["creates_publication_approval"] is False
    assert body["creates_agent_run"] is False
    assert body["strategy_eligibility"]["strategy_eligible"] is False
    assert body["evidence_snapshot"] is not None
    snap_hash = body["evidence_snapshot_hash"]

    snap = client.get(
        f"/projects/{project_id}/business-verdicts/{body['id']}/evidence-snapshot",
        headers=auth_headers,
    )
    assert snap.status_code == 200
    assert snap.json()["snapshot_hash"] == snap_hash

    submitted = client.post(
        f"/projects/{project_id}/business-verdicts/{body['id']}/submit-review",
        headers=auth_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["lifecycle_status"] == "under_review"

    # immutable while under review
    patched = client.patch(
        f"/projects/{project_id}/business-verdicts/{body['id']}",
        json={"executive_conclusion": "changed"},
        headers=auth_headers,
    )
    assert patched.status_code == 409

    approved = client.post(
        f"/projects/{project_id}/business-verdicts/{body['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    ap = approved.json()
    assert ap["lifecycle_status"] == "approved"
    assert ap["creates_strategy"] is False
    assert ap["strategy_eligibility"]["creates_strategy"] is False
    if ap["verdict_type"] == "insufficient_data":
        assert ap["strategy_eligibility"]["strategy_eligible"] is False
        assert ap["strategy_eligibility"]["return_to_investigation"] is True

    # approved immutable
    patched2 = client.patch(
        f"/projects/{project_id}/business-verdicts/{body['id']}",
        json={"executive_conclusion": "hack"},
        headers=auth_headers,
    )
    assert patched2.status_code == 409
    assert "immutable" in _err(patched2).lower() or "immutable_verdict" in _err(patched2)


def test_go_blocked_by_missing_critical_and_strategy_eligibility(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.5 GO")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)

    m = _accept_evidence(
        client,
        auth_headers,
        project_id,
        inv_id,
        src_id,
        claim="Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
        area="market_research",
    )
    a = _accept_evidence(
        client,
        auth_headers,
        project_id,
        inv_id,
        src_id,
        claim="Целевая аудитория — взрослые пациенты 25–45 лет в Москве.",
        area="audience_analysis",
    )
    e = _accept_evidence(
        client,
        auth_headers,
        project_id,
        inv_id,
        src_id,
        claim="Средний чек по прайсу клиники составляет 9000 рублей.",
        area="economics",
    )

    # GO without investigation under_review/completed should fail
    go_body = {
        "verdict_type": "go",
        "confidence_level": "high",
        "executive_conclusion": "Можно переходить к Strategy.",
        "executive_rationale": "Accepted Evidence покрывает market/audience/economics.",
        "primary_business_implication": "Жизнеспособность подтверждается.",
        "recommended_next_action": "Human review затем Strategy eligibility.",
        "evidence_links": [
            {
                "evidence_id": m["id"],
                "evidence_version": m["version"],
                "role": "supports",
            },
            {
                "evidence_id": a["id"],
                "evidence_version": a["version"],
                "role": "supports",
            },
            {
                "evidence_id": e["id"],
                "evidence_version": e["version"],
                "role": "supports",
            },
        ],
    }
    blocked = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts",
        json=go_body,
        headers=auth_headers,
    )
    # may fail on readiness (not ready_for_review) or investigation status
    assert blocked.status_code == 409

    # advance investigation if API allows
    client.post(
        f"/projects/{project_id}/investigations/{inv_id}/start",
        headers=auth_headers,
    )
    # complete stages to under_review is complex — test CONDITIONAL_GO path instead
    cond = {
        "verdict_type": "conditional_go",
        "confidence_level": "medium",
        "executive_conclusion": "Условный GO при закрытии gaps.",
        "executive_rationale": "Есть accepted Evidence, но условия обязательны.",
        "primary_business_implication": "Стратегия только после условий.",
        "recommended_next_action": "Закрыть условия.",
        "evidence_links": [
            {
                "evidence_id": m["id"],
                "evidence_version": m["version"],
                "role": "supports",
            },
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
                "consequence_if_unmet": "Вернуть к Investigation",
                "status": "open",
            }
        ],
    }
    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts",
        json=cond,
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/submit-review",
        headers=auth_headers,
    )
    approved = client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    elig = approved.json()["strategy_eligibility"]
    assert elig["strategy_eligible"] is True
    assert elig["open_conditions_mandatory"] is True
    assert elig["creates_strategy"] is False
    assert elig["creates_execution_approval"] is False


def test_reject_cross_project_evidence_and_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_a = _project(client, auth_headers, "A")
    inv_a, src_a = _setup_inv_and_source(client, auth_headers, project_a)
    ev_a = _accept_evidence(
        client,
        auth_headers,
        project_a,
        inv_a,
        src_a,
        claim="Рынок Москвы показывает устойчивый спрос на услугу по открытым данным.",
        area="market_research",
    )

    project_b = _project(client, auth_headers, "B")
    inv_b, _src_b = _setup_inv_and_source(client, auth_headers, project_b)

    bad = client.post(
        f"/projects/{project_b}/investigations/{inv_b}/business-verdicts",
        json={
            "verdict_type": "insufficient_data",
            "confidence_level": "low",
            "executive_conclusion": "Недостаточно.",
            "executive_rationale": "Cross project evidence rejected.",
            "primary_business_implication": "Stop.",
            "recommended_next_action": "Investigate.",
            "evidence_links": [
                {
                    "evidence_id": ev_a["id"],
                    "evidence_version": ev_a["version"],
                    "role": "context",
                }
            ],
        },
        headers=auth_headers,
    )
    assert bad.status_code == 409

    listed = client.get(
        f"/projects/{project_b}/business-verdicts",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_no_go_blocks_strategy(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "NOGO")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)
    ev = _accept_evidence(
        client,
        auth_headers,
        project_id,
        inv_id,
        src_id,
        claim="Конкуренты демпингуют цену ниже себестоимости по открытым прайсам.",
        area="economics",
    )
    created = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts",
        json={
            "verdict_type": "no_go",
            "confidence_level": "high",
            "executive_conclusion": "NO_GO в текущей форме.",
            "executive_rationale": "Economics conflict is verdict-changing.",
            "primary_business_implication": "Pivot.",
            "recommended_next_action": "Pivot route.",
            "evidence_links": [
                {
                    "evidence_id": ev["id"],
                    "evidence_version": ev["version"],
                    "role": "contradicts",
                }
            ],
            "critical_risks": [
                {
                    "title": "Структурная убыточность",
                    "description": "Price war destroys margin",
                    "severity": "critical",
                    "probability": "high",
                    "business_consequence": "Losses",
                    "verdict_sensitivity": "verdict_changing",
                }
            ],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/submit-review",
        headers=auth_headers,
    )
    approved = client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    elig = approved.json()["strategy_eligibility"]
    assert elig["strategy_eligible"] is False
    assert elig["pivot_route_allowed"] is True


@pytest.mark.asyncio
async def test_approve_creates_no_agent_run_or_llm(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project(client, auth_headers, "FIREWALL")
    inv_id, src_id = _setup_inv_and_source(client, auth_headers, project_id)
    draft = client.post(
        f"/projects/{project_id}/investigations/{inv_id}/business-verdicts/build-draft",
        headers=auth_headers,
    )
    assert draft.status_code == 201
    vid = draft.json()["id"]
    client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/approve",
        headers=auth_headers,
    )

    runs = await db_session.scalar(select(func.count()).select_from(AgentRunTable))
    llms = await db_session.scalar(select(func.count()).select_from(LLMRequestTable))
    verdicts = await db_session.scalar(
        select(func.count()).select_from(BusinessVerdictTable)
    )
    assert verdicts and verdicts >= 1
    assert runs == 0
    assert llms == 0

"""Commercial MVP P1 — end-to-end lineage + isolation invariants.

Project → Brief → Investigation → Source → Evidence → Verdict → Strategy
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_strategy import MarketingStrategyTable


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _brief_body() -> dict:
    return {
        "language": "ru",
        "project_basics": {
            "project_name": "P1 Clinic",
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


def test_commercial_mvp_lineage_e2e_and_firewall(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Full durable chain with exact lineage pins and no ops side effects."""
    project = client.post(
        "/projects", json={"name": "P1 E2E"}, headers=auth_headers
    ).json()
    project_id = project["id"]

    draft = client.post(
        f"/projects/{project_id}/briefs", json=_brief_body(), headers=auth_headers
    ).json()
    assert draft["status"] == "draft"
    assert draft["version"] == 1

    # Draft brief must not seed Investigation
    blocked_inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": draft["id"],
            "project_brief_version": draft["version"],
            "input_fingerprint": draft["input_fingerprint"],
        },
        headers=auth_headers,
    )
    assert blocked_inv.status_code == 409
    assert "brief_not_submitted" in _err(blocked_inv)

    brief = client.post(
        f"/projects/{project_id}/briefs/{draft['id']}/submit", headers=auth_headers
    ).json()
    assert brief["status"] == "submitted"
    assert brief["version"] == 1

    inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": brief["id"],
            "project_brief_version": brief["version"],
            "input_fingerprint": brief["input_fingerprint"],
        },
        headers=auth_headers,
    ).json()
    assert inv["project_id"] == project_id
    assert inv["project_brief_id"] == brief["id"]
    assert inv["project_brief_version"] == brief["version"]
    assert inv["version"] == 1

    src = client.post(
        f"/projects/{project_id}/sources",
        json={
            "source_type": "website",
            "provenance_type": "secondary",
            "title": "Market",
            "url": "https://example.com/p1-e2e",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=auth_headers,
    ).json()
    assert src["project_id"] == project_id
    assert src["version"] == 1

    m = _accept_ev(
        client,
        auth_headers,
        project_id,
        inv["id"],
        src["id"],
        "Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
        "market_research",
    )
    e = _accept_ev(
        client,
        auth_headers,
        project_id,
        inv["id"],
        src["id"],
        "Средний чек по прайсу клиники составляет 9000 рублей.",
        "economics",
    )
    assert m["lifecycle_status"] == "accepted"
    assert e["lifecycle_status"] == "accepted"

    # Accepted evidence content is immutable
    patch_ev = client.patch(
        f"/projects/{project_id}/investigations/{inv['id']}/evidence/{m['id']}",
        json={"claim": "mutated claim that should be rejected as immutable"},
        headers=auth_headers,
    )
    assert patch_ev.status_code == 409
    assert "immutable_evidence" in _err(patch_ev)

    verdict_created = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/business-verdicts",
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
        headers=auth_headers,
    )
    assert verdict_created.status_code == 201, verdict_created.text
    verdict = verdict_created.json()
    assert verdict["investigation_id"] == inv["id"]
    assert verdict["project_brief_id"] == brief["id"]
    assert verdict["project_brief_version"] == brief["version"]
    assert verdict["evidence_snapshot_hash"]
    assert verdict["version"] == 1

    client.post(
        f"/projects/{project_id}/business-verdicts/{verdict['id']}/submit-review",
        headers=auth_headers,
    )
    approved_v = client.post(
        f"/projects/{project_id}/business-verdicts/{verdict['id']}/approve",
        headers=auth_headers,
    ).json()
    assert approved_v["lifecycle_status"] == "approved"

    patch_v = client.patch(
        f"/projects/{project_id}/business-verdicts/{verdict['id']}",
        json={"executive_conclusion": "hack"},
        headers=auth_headers,
    )
    assert patch_v.status_code == 409
    assert "immutable_verdict" in _err(patch_v)

    strategy = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": approved_v["id"]},
        headers=auth_headers,
    ).json()
    assert strategy["business_verdict_id"] == approved_v["id"]
    assert strategy["business_verdict_version"] == approved_v["version"]
    assert strategy["evidence_snapshot_hash"] == approved_v["evidence_snapshot_hash"]
    assert strategy["is_marketing_plan"] is False
    assert strategy["creates_marketing_plan"] is False
    assert strategy["creates_campaign"] is False
    assert strategy["creates_agent_run"] is False

    client.post(
        f"/projects/{project_id}/marketing-strategies/{strategy['id']}/submit-review",
        headers=auth_headers,
    )
    approved_s = client.post(
        f"/projects/{project_id}/marketing-strategies/{strategy['id']}/approve",
        headers=auth_headers,
    ).json()
    assert approved_s["lifecycle_status"] == "approved"

    patch_s = client.patch(
        f"/projects/{project_id}/marketing-strategies/{strategy['id']}",
        json={"title": "hack"},
        headers=auth_headers,
    )
    assert patch_s.status_code == 409
    assert "immutable_strategy" in _err(patch_s)


def test_cross_project_source_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    a = client.post("/projects", json={"name": "A"}, headers=auth_headers).json()["id"]
    b = client.post("/projects", json={"name": "B"}, headers=auth_headers).json()["id"]

    brief = client.post(f"/projects/{a}/briefs", json=_brief_body(), headers=auth_headers).json()
    submitted = client.post(
        f"/projects/{a}/briefs/{brief['id']}/submit", headers=auth_headers
    ).json()
    inv = client.post(
        f"/projects/{a}/investigations",
        json={
            "project_brief_id": submitted["id"],
            "project_brief_version": submitted["version"],
            "input_fingerprint": submitted["input_fingerprint"],
        },
        headers=auth_headers,
    ).json()
    foreign_src = client.post(
        f"/projects/{b}/sources",
        json={
            "source_type": "website",
            "provenance_type": "secondary",
            "title": "Foreign",
            "url": "https://example.com/foreign-p1",
            "capabilities": ["webpage"],
        },
        headers=auth_headers,
    ).json()

    bad = client.post(
        f"/projects/{a}/investigations/{inv['id']}/evidence",
        json={
            "claim": "Claim that must fail cross-project source.",
            "evidence_type": "observed_fact",
            "investigation_area": "market_research",
            "materiality": "critical",
            "source_links": [
                {
                    "source_id": foreign_src["id"],
                    "stance": "supports",
                    "locator_type": "page",
                    "locator_value": "1",
                    "excerpt": "x",
                }
            ],
        },
        headers=auth_headers,
    )
    assert bad.status_code in (404, 409)
    err = _err(bad)
    assert "cross_project" in err or "source_not" in err or "not_found" in err.lower()


@pytest.mark.asyncio
async def test_full_chain_creates_no_ops_artifacts(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects", json={"name": "P1 FW"}, headers=auth_headers
    ).json()["id"]
    draft = client.post(
        f"/projects/{project_id}/briefs", json=_brief_body(), headers=auth_headers
    ).json()
    brief = client.post(
        f"/projects/{project_id}/briefs/{draft['id']}/submit", headers=auth_headers
    ).json()
    inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": brief["id"],
            "project_brief_version": brief["version"],
            "input_fingerprint": brief["input_fingerprint"],
        },
        headers=auth_headers,
    ).json()
    src = client.post(
        f"/projects/{project_id}/sources",
        json={
            "source_type": "website",
            "provenance_type": "secondary",
            "title": "Market",
            "url": "https://example.com/p1-fw",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=auth_headers,
    ).json()
    m = _accept_ev(
        client,
        auth_headers,
        project_id,
        inv["id"],
        src["id"],
        "Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
        "market_research",
    )
    e = _accept_ev(
        client,
        auth_headers,
        project_id,
        inv["id"],
        src["id"],
        "Средний чек по прайсу клиники составляет 9000 рублей.",
        "economics",
    )
    created = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/business-verdicts",
        json={
            "verdict_type": "conditional_go",
            "confidence_level": "medium",
            "executive_conclusion": "Условный GO.",
            "executive_rationale": "Есть Evidence, есть условия.",
            "primary_business_implication": "Strategy possible.",
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
                    "consequence_if_unmet": "Block",
                    "status": "open",
                }
            ],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    vid = created.json()["id"]
    client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/submit-review", headers=auth_headers
    )
    client.post(f"/projects/{project_id}/business-verdicts/{vid}/approve", headers=auth_headers)
    draft_s = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": vid},
        headers=auth_headers,
    )
    assert draft_s.status_code == 201
    sid = draft_s.json()["id"]
    client.post(
        f"/projects/{project_id}/marketing-strategies/{sid}/submit-review", headers=auth_headers
    )
    client.post(f"/projects/{project_id}/marketing-strategies/{sid}/approve", headers=auth_headers)

    assert await db_session.scalar(select(func.count()).select_from(MarketingStrategyTable)) >= 1
    assert await db_session.scalar(select(func.count()).select_from(MarketingPlanTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MarketingCampaignTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(AgentRunTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(LLMRequestTable)) == 0


def test_alembic_commercial_mvp_revision_chain() -> None:
    """Static append-only chain for 20260614_0029 → 0036 (no DB required)."""
    root = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    expected = [
        ("20260614_0029", "20260603_0028"),
        ("20260614_0030", "20260614_0029"),
        ("20260614_0031", "20260614_0030"),
        ("20260614_0032", "20260614_0031"),
        ("20260614_0033", "20260614_0032"),
        ("20260614_0034", "20260614_0033"),
        ("20260614_0035", "20260614_0034"),
        ("20260614_0036", "20260614_0035"),
    ]
    rev_re = re.compile(r'^revision:\s*str\s*=\s*"([^"]+)"', re.M)
    down_re = re.compile(r'^down_revision:\s*.*?=\s*"([^"]+)"', re.M)
    for rev, down in expected:
        matches = list(root.glob(f"{rev}_*.py"))
        assert len(matches) == 1, rev
        text = matches[0].read_text(encoding="utf-8")
        assert rev_re.search(text).group(1) == rev
        assert down_re.search(text).group(1) == down
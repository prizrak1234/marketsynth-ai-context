"""Commercial MVP P1.3 — end-to-end freeze + ownership + migration chain."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.implementation_marketing_plan_handoff import (
    ImplementationMarketingPlanHandoffTable,
)
from app.db.models.implementation_plan import ImplementationPlanTable
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.domain.implementation_marketing_plan_handoff_engine import (
    compute_mapping_fingerprint,
)
from app.domain.project_brief_fingerprint import compute_project_brief_fingerprint
from app.schemas.contracts import ProjectBriefContent


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _brief_body() -> dict:
    return {
        "language": "ru",
        "project_basics": {
            "project_name": "P1.3 Clinic",
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


def _accept_ev(client, headers, project_id, inv_id, src_id, claim, area) -> dict:
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


def _run_full_chain_to_draft(
    client: TestClient, headers: dict[str, str], name: str = "P1.3 E2E"
) -> dict:
    """Run Project → … → MarketingPlan draft; return lineage snapshot."""
    project = client.post("/projects", json={"name": name}, headers=headers).json()
    project_id = project["id"]

    draft = client.post(
        f"/projects/{project_id}/briefs", json=_brief_body(), headers=headers
    ).json()
    assert draft["status"] == "draft"
    assert draft["version"] == 1

    brief = client.post(
        f"/projects/{project_id}/briefs/{draft['id']}/submit", headers=headers
    ).json()
    assert brief["status"] == "submitted"

    inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": brief["id"],
            "project_brief_version": brief["version"],
            "input_fingerprint": brief["input_fingerprint"],
        },
        headers=headers,
    ).json()
    assert inv["project_brief_id"] == brief["id"]
    assert inv["project_brief_version"] == brief["version"]
    assert inv["input_fingerprint"] == brief["input_fingerprint"]

    # Optional start if route exists; ignore if already active
    client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/start",
        headers=headers,
    )

    src = client.post(
        f"/projects/{project_id}/sources",
        json={
            "source_type": "website",
            "provenance_type": "secondary",
            "title": "Market",
            "url": f"https://example.com/{name}",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=headers,
    ).json()
    assert src["project_id"] == project_id

    m = _accept_ev(
        client,
        headers,
        project_id,
        inv["id"],
        src["id"],
        "Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
        "market_research",
    )
    e = _accept_ev(
        client,
        headers,
        project_id,
        inv["id"],
        src["id"],
        "Средний чек по прайсу клиники составляет 9000 рублей.",
        "economics",
    )

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
        headers=headers,
    )
    assert verdict_created.status_code == 201, verdict_created.text
    verdict = verdict_created.json()
    assert verdict["evidence_snapshot_hash"]
    assert verdict["investigation_id"] == inv["id"]
    assert verdict["project_brief_version"] == brief["version"]

    client.post(
        f"/projects/{project_id}/business-verdicts/{verdict['id']}/submit-review",
        headers=headers,
    )
    approved_v = client.post(
        f"/projects/{project_id}/business-verdicts/{verdict['id']}/approve",
        headers=headers,
    ).json()
    assert approved_v["lifecycle_status"] == "approved"

    strategy = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": approved_v["id"]},
        headers=headers,
    ).json()
    assert strategy["business_verdict_id"] == approved_v["id"]
    assert strategy["business_verdict_version"] == approved_v["version"]
    assert strategy["evidence_snapshot_hash"] == approved_v["evidence_snapshot_hash"]
    assert strategy["creates_marketing_plan"] is False

    client.post(
        f"/projects/{project_id}/marketing-strategies/{strategy['id']}/submit-review",
        headers=headers,
    )
    approved_s = client.post(
        f"/projects/{project_id}/marketing-strategies/{strategy['id']}/approve",
        headers=headers,
    ).json()
    assert approved_s["lifecycle_status"] == "approved"
    assert approved_s["creates_marketing_plan"] is False

    impl_draft = client.post(
        f"/projects/{project_id}/implementation-plans/build-draft",
        json={"marketing_strategy_id": approved_s["id"]},
        headers=headers,
    )
    assert impl_draft.status_code == 201, impl_draft.text
    impl_body = impl_draft.json()
    assert impl_body["marketing_strategy_id"] == approved_s["id"]
    assert impl_body["marketing_strategy_version"] == approved_s["version"]
    assert impl_body["business_verdict_id"] == approved_s["business_verdict_id"]
    assert impl_body["creates_marketing_plan"] is False

    mappable = [
        t
        for t in impl_body["tasks"]
        if t.get("responsible_role")
        in (
            "Research Director",
            "Chief Marketing Strategist",
            "Content Strategist",
            "Copywriter",
            "Analyst",
            "Market Analyst",
            "Risk Officer",
        )
    ] or impl_body["tasks"]
    patched = client.patch(
        f"/projects/{project_id}/implementation-plans/{impl_body['id']}",
        json={
            "conditions": [],
            "implementation_risks": [],
            "budget_gates": [
                {**g, "lifecycle_status": "not_required"} for g in impl_body["budget_gates"]
            ],
            "approval_gates": [
                {**g, "lifecycle_status": "not_required"} for g in impl_body["approval_gates"]
            ],
            "tasks": [
                {
                    **t,
                    "dependency_ids": [],
                    "approval_required": False,
                    "approval_gate_id": None,
                    "mapping_eligibility": "transformable",
                    "blocked_reason": None,
                }
                for t in mappable
            ],
            "dependencies": [],
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    plan = patched.json()
    assert plan["readiness_status"] == "ready_for_handoff", plan.get("readiness_reasons")

    client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/submit-review",
        headers=headers,
    )
    approved_plan = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/approve",
        headers=headers,
    ).json()
    assert approved_plan["lifecycle_status"] == "approved"
    assert approved_plan["creates_marketing_plan"] is False

    # ImplementationPlan approve ≠ handoff / MarketingPlan
    assert (
        client.get(
            f"/projects/{project_id}/marketing-plans",
            headers=headers,
        ).json()
        == []
        or len(client.get(f"/projects/{project_id}/marketing-plans", headers=headers).json()) == 0
    )

    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{approved_plan['id']}/marketing-plan-handoff/preview",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    pv = preview.json()
    assert pv["creates_marketing_plan_draft"] is False
    assert pv["creates_agent_run"] is False
    assert pv["side_effects"] == []
    assert pv["implementation_plan_version"] == approved_plan["version"]
    assert pv["mapping_version"] == "implementation_to_marketing_plan.v1"

    # Preview alone must not create MarketingPlan
    plans_after_preview = client.get(
        f"/projects/{project_id}/marketing-plans", headers=headers
    ).json()
    assert plans_after_preview == []

    confirm = client.post(
        f"/projects/{project_id}/implementation-plans/{approved_plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": pv["handoff_id"],
            "mapping_fingerprint": pv["mapping_fingerprint"],
            "expected_implementation_plan_version": approved_plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=headers,
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["marketing_plan_status"] == "draft"
    assert body["creates_marketing_plan_approval"] is False
    assert body["dispatches_specialist_tasks"] is False
    assert body["creates_agent_run"] is False
    assert body["creates_campaign"] is False

    mp = client.get(
        f"/projects/{project_id}/marketing-plans/{body['marketing_plan_id']}",
        headers=headers,
    ).json()
    assert mp["status"] == "draft"
    assert mp["current_version_number"] == body["marketing_plan_version"]
    ctx = mp.get("project_context") or {}
    assert ctx.get("source") == "commercial_mvp_p1_2_handoff"
    assert ctx.get("source_implementation_plan_id") == approved_plan["id"]
    assert ctx.get("source_implementation_plan_version") == approved_plan["version"]
    assert ctx.get("source_marketing_strategy_id") == approved_s["id"]
    assert ctx.get("handoff_id") == body["handoff_id"]
    assert ctx.get("mapping_fingerprint") == pv["mapping_fingerprint"]

    # Idempotent confirm
    confirm2 = client.post(
        f"/projects/{project_id}/implementation-plans/{approved_plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": pv["handoff_id"],
            "mapping_fingerprint": pv["mapping_fingerprint"],
            "expected_implementation_plan_version": approved_plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=headers,
    )
    assert confirm2.status_code == 200
    assert confirm2.json()["idempotent_replay"] is True
    assert confirm2.json()["marketing_plan_id"] == body["marketing_plan_id"]

    return {
        "project_id": project_id,
        "brief": brief,
        "inv": inv,
        "src": src,
        "evidence": (m, e),
        "verdict": approved_v,
        "strategy": approved_s,
        "plan": approved_plan,
        "preview": pv,
        "confirm": body,
        "marketing_plan": mp,
    }


def test_p1_3_full_chain_lineage_and_draft_only(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    snap = _run_full_chain_to_draft(client, auth_headers)
    brief = snap["brief"]
    inv = snap["inv"]
    strategy = snap["strategy"]
    plan = snap["plan"]
    mp = snap["marketing_plan"]

    assert inv["project_brief_id"] == brief["id"]
    assert inv["project_brief_version"] == brief["version"]
    assert strategy["business_verdict_version"] == snap["verdict"]["version"]
    assert plan["marketing_strategy_version"] == strategy["version"]
    assert plan["evidence_snapshot_hash"] == strategy["evidence_snapshot_hash"]
    assert mp["status"] == "draft"
    assert mp["approved_version_number"] in (None, 0) or mp.get("approved_version_number") is None


def test_p1_3_cross_owner_handoff_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    snap = _run_full_chain_to_draft(client, auth_headers, "P1.3-owner")
    project_id = snap["project_id"]
    plan_id = snap["plan"]["id"]
    mp_id = snap["confirm"]["marketing_plan_id"]

    assert (
        client.post(
            f"/projects/{project_id}/implementation-plans/{plan_id}/marketing-plan-handoff/preview",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/projects/{project_id}/marketing-plans/{mp_id}",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert client.get(f"/projects/{project_id}", headers=other_auth_headers).status_code == 404


@pytest.mark.asyncio
async def test_p1_3_execution_firewall_after_full_chain(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    snap = _run_full_chain_to_draft(client, auth_headers, "P1.3-fw")
    assert snap["confirm"]["marketing_plan_status"] == "draft"

    assert await db_session.scalar(select(func.count()).select_from(MarketingPlanTable)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ImplementationPlanTable)) >= 1
    assert (
        await db_session.scalar(
            select(func.count()).select_from(ImplementationMarketingPlanHandoffTable)
        )
        >= 1
    )
    assert await db_session.scalar(select(func.count()).select_from(AgentRunTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(LLMRequestTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MarketingCampaignTable)) == 0
    assert (
        await db_session.scalar(select(func.count()).select_from(MarketingPlanExecutionRunTable))
        == 0
    )


def test_p1_3_stale_handoff_preview_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    snap = _run_full_chain_to_draft(client, auth_headers, "P1.3-stale")
    bad = client.post(
        f"/projects/{snap['project_id']}/implementation-plans/{snap['plan']['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": snap["preview"]["handoff_id"],
            "mapping_fingerprint": "f" * 64,
            "expected_implementation_plan_version": snap["plan"]["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert bad.status_code == 409
    assert "fingerprint_mismatch" in _err(bad)


def test_p1_3_fingerprint_reproducibility() -> None:
    content = ProjectBriefContent.model_validate(_brief_body())
    a = compute_project_brief_fingerprint(content)
    b = compute_project_brief_fingerprint(content)
    assert a == b
    assert len(a) >= 32

    fp1 = compute_mapping_fingerprint(
        plan_id="11111111-1111-1111-1111-111111111111",
        plan_version=1,
        mapping_version="implementation_to_marketing_plan.v1",
        policy="create_new_draft",
        mapped_payload=[
            {
                "implementation_task_id": "t2",
                "specialist": "researcher",
                "objective": "b",
                "expected_output": "o",
                "classification": "transformable",
            },
            {
                "implementation_task_id": "t1",
                "specialist": "strategist",
                "objective": "a",
                "expected_output": "o",
                "classification": "exact",
            },
        ],
    )
    fp2 = compute_mapping_fingerprint(
        plan_id="11111111-1111-1111-1111-111111111111",
        plan_version=1,
        mapping_version="implementation_to_marketing_plan.v1",
        policy="create_new_draft",
        mapped_payload=[
            {
                "implementation_task_id": "t1",
                "specialist": "strategist",
                "objective": "a",
                "expected_output": "o",
                "classification": "exact",
            },
            {
                "implementation_task_id": "t2",
                "specialist": "researcher",
                "objective": "b",
                "expected_output": "o",
                "classification": "transformable",
            },
        ],
    )
    assert fp1 == fp2


def test_alembic_commercial_mvp_revision_chain_through_0036() -> None:
    """Static append-only chain 20260614_0029 → 0036 (no DB required)."""
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

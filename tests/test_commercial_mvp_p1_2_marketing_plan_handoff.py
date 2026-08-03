"""Commercial MVP P1.2 — ImplementationPlan → MarketingPlan draft handoff tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.implementation_marketing_plan_handoff import (
    ImplementationMarketingPlanHandoffTable,
)
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


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


def _approved_strategy(client: TestClient, headers: dict[str, str], name: str = "P1.2") -> tuple[str, dict]:
    project_id = client.post("/projects", json={"name": name}, headers=headers).json()["id"]
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
            "url": f"https://example.com/{name}",
            "capabilities": ["webpage", "text"],
            "attach_to_investigation_id": inv["id"],
        },
        headers=headers,
    ).json()
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
    created = client.post(
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
    assert created.status_code == 201, created.text
    vid = created.json()["id"]
    client.post(f"/projects/{project_id}/business-verdicts/{vid}/submit-review", headers=headers)
    verdict = client.post(
        f"/projects/{project_id}/business-verdicts/{vid}/approve", headers=headers
    ).json()
    draft = client.post(
        f"/projects/{project_id}/marketing-strategies/build-draft",
        json={"business_verdict_id": verdict["id"]},
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    sid = draft.json()["id"]
    client.post(
        f"/projects/{project_id}/marketing-strategies/{sid}/submit-review", headers=headers
    )
    strategy = client.post(
        f"/projects/{project_id}/marketing-strategies/{sid}/approve", headers=headers
    ).json()
    return project_id, strategy


def _approved_ready_impl_plan(client, headers, project_id, strategy) -> dict:
    draft = client.post(
        f"/projects/{project_id}/implementation-plans/build-draft",
        json={"marketing_strategy_id": strategy["id"]},
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    body = draft.json()
    mappable_tasks = [
        t
        for t in body["tasks"]
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
    ]
    if not mappable_tasks:
        mappable_tasks = body["tasks"]
    patched = client.patch(
        f"/projects/{project_id}/implementation-plans/{body['id']}",
        json={
            "conditions": [],
            "implementation_risks": [],
            "budget_gates": [
                {**g, "lifecycle_status": "not_required"} for g in body["budget_gates"]
            ],
            "approval_gates": [
                {**g, "lifecycle_status": "not_required"} for g in body["approval_gates"]
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
                for t in mappable_tasks
            ],
            "dependencies": [],
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    plan = patched.json()
    assert plan["readiness_status"] == "ready_for_handoff", (
        plan["readiness_status"],
        plan.get("readiness_reasons"),
    )
    client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/submit-review",
        headers=headers,
    )
    approved = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_preview_and_confirm_creates_draft_only(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id, strategy = _approved_strategy(client, auth_headers)
    plan = _approved_ready_impl_plan(client, auth_headers, project_id, strategy)
    assert plan["readiness_status"] == "ready_for_handoff"

    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200, preview.text
    pv = preview.json()
    assert pv["side_effects"] == []
    assert pv["creates_marketing_plan_draft"] is False
    assert pv["creates_agent_run"] is False
    assert pv["mapping_version"] == "implementation_to_marketing_plan.v1"
    assert len(pv["included_tasks"]) + len(pv["transformed_tasks"]) >= 1

    confirm = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": pv["handoff_id"],
            "mapping_fingerprint": pv["mapping_fingerprint"],
            "expected_implementation_plan_version": plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["marketing_plan_status"] == "draft"
    assert body["creates_marketing_plan_approval"] is False
    assert body["creates_agent_run"] is False
    assert body["dispatches_specialist_tasks"] is False
    assert body["idempotent_replay"] is False

    confirm2 = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": pv["handoff_id"],
            "mapping_fingerprint": pv["mapping_fingerprint"],
            "expected_implementation_plan_version": plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert confirm2.status_code == 200
    assert confirm2.json()["idempotent_replay"] is True
    assert confirm2.json()["marketing_plan_id"] == body["marketing_plan_id"]

    # fingerprint mismatch
    bad_fp = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": pv["handoff_id"],
            "mapping_fingerprint": "0" * 64,
            "expected_implementation_plan_version": plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert bad_fp.status_code == 409
    assert "fingerprint_mismatch" in _err(bad_fp)


def test_confirm_requires_explicit_confirmation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id, strategy = _approved_strategy(client, auth_headers, "P1.2-exp")
    plan = _approved_ready_impl_plan(client, auth_headers, project_id, strategy)
    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/preview",
        headers=auth_headers,
    ).json()
    bad = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": preview["handoff_id"],
            "mapping_fingerprint": preview["mapping_fingerprint"],
            "expected_implementation_plan_version": plan["version"],
            "explicit_confirmation": False,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert bad.status_code == 409
    assert "explicit_confirmation" in _err(bad)


def test_reject_unapproved_plan_confirm(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id, strategy = _approved_strategy(client, auth_headers, "P1.2-unapp")
    draft = client.post(
        f"/projects/{project_id}/implementation-plans/build-draft",
        json={"marketing_strategy_id": strategy["id"]},
        headers=auth_headers,
    ).json()
    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{draft['id']}/marketing-plan-handoff/preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    blocked = client.post(
        f"/projects/{project_id}/implementation-plans/{draft['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": preview.json()["handoff_id"],
            "mapping_fingerprint": preview.json()["mapping_fingerprint"],
            "expected_implementation_plan_version": draft["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert blocked.status_code == 409
    assert "implementation_plan_not_approved" in _err(blocked) or "readiness" in _err(blocked)


def test_unsupported_role_classification(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id, strategy = _approved_strategy(client, auth_headers, "P1.2-role")
    draft = client.post(
        f"/projects/{project_id}/implementation-plans/build-draft",
        json={"marketing_strategy_id": strategy["id"]},
        headers=auth_headers,
    ).json()
    tasks = [
        {
            **t,
            "responsible_role": "Client Owner",
            "mapping_eligibility": "unsupported",
            "dependency_ids": [],
        }
        for t in draft["tasks"][:1]
    ] + [
        {
            **t,
            "dependency_ids": [],
            "approval_required": False,
            "mapping_eligibility": "transformable",
        }
        for t in draft["tasks"][1:3]
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
    ]
    if len(tasks) < 2:
        tasks = draft["tasks"]
    patched = client.patch(
        f"/projects/{project_id}/implementation-plans/{draft['id']}",
        json={
            "conditions": [],
            "implementation_risks": [],
            "budget_gates": [
                {**g, "lifecycle_status": "not_required"} for g in draft["budget_gates"]
            ],
            "approval_gates": [
                {**g, "lifecycle_status": "not_required"} for g in draft["approval_gates"]
            ],
            "tasks": tasks,
            "dependencies": [],
        },
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{draft['id']}/marketing-plan-handoff/preview",
        headers=auth_headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert any(t["classification"] == "unsupported" for t in body["unsupported_tasks"]) or any(
        t["classification"] == "unsupported" for t in body.get("excluded_tasks", [])
    )


@pytest.mark.asyncio
async def test_handoff_firewall_no_runs_campaigns_approvals(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, strategy = _approved_strategy(client, auth_headers, "P1.2-fw")
    plan = _approved_ready_impl_plan(client, auth_headers, project_id, strategy)
    preview = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/preview",
        headers=auth_headers,
    ).json()
    confirm = client.post(
        f"/projects/{project_id}/implementation-plans/{plan['id']}/marketing-plan-handoff/confirm",
        json={
            "handoff_preview_id": preview["handoff_id"],
            "mapping_fingerprint": preview["mapping_fingerprint"],
            "expected_implementation_plan_version": plan["version"],
            "explicit_confirmation": True,
            "existing_plan_policy": "create_new_draft",
        },
        headers=auth_headers,
    )
    assert confirm.status_code == 200, confirm.text

    plans = await db_session.scalar(select(func.count()).select_from(MarketingPlanTable))
    handoffs = await db_session.scalar(
        select(func.count()).select_from(ImplementationMarketingPlanHandoffTable)
    )
    assert plans == 1
    assert handoffs >= 1
    assert await db_session.scalar(select(func.count()).select_from(AgentRunTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(LLMRequestTable)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MarketingCampaignTable)) == 0
    assert (
        await db_session.scalar(select(func.count()).select_from(MarketingPlanExecutionRunTable))
        == 0
    )

    row = (await db_session.execute(select(MarketingPlanTable))).scalar_one()
    assert str(row.status) == "draft" or row.status.value == "draft"
    ctx = row.project_context or {}
    assert ctx.get("source") == "commercial_mvp_p1_2_handoff"
    assert ctx.get("handoff_id")
    assert ctx.get("source_implementation_plan_id") == plan["id"]

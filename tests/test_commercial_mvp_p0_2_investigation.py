"""Commercial MVP P0.2 — Investigation domain API tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.investigation import InvestigationTable
from app.db.models.llm import LLMRequestTable
from app.services.investigation_service import InvestigationService


def _project(client: TestClient, headers: dict[str, str], name: str = "P0.2 Inv") -> str:
    r = client.post("/projects", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def _brief_body(**overrides: object) -> dict:
    body: dict = {
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
        "readiness_reasons": ["pending evidence"],
    }
    body.update(overrides)
    return body


def _submitted_brief(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    created = client.post(
        f"/projects/{project_id}/briefs",
        json=_brief_body(),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    brief = created.json()
    submitted = client.post(
        f"/projects/{project_id}/briefs/{brief['id']}/submit",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def _create_payload(brief: dict) -> dict:
    return {
        "project_brief_id": brief["id"],
        "project_brief_version": brief["version"],
        "input_fingerprint": brief["input_fingerprint"],
    }


def test_create_lifecycle_and_no_side_effects(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    brief = _submitted_brief(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    inv = created.json()
    assert inv["status"] == "draft"
    assert inv["project_brief_id"] == brief["id"]
    assert inv["project_brief_version"] == brief["version"]
    assert len(inv["stages"]) == 9
    assert inv["metadata"].get("source_evidence")

    started = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    assert started.json()["status"] == "active"
    assert started.json()["started_at"] is not None

    blocked = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/block",
        json={"reason": "missing data"},
        headers=auth_headers,
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    resumed = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/resume",
        headers=auth_headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "ready"

    started2 = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/start",
        headers=auth_headers,
    )
    assert started2.status_code == 200
    assert started2.json()["status"] == "active"

    review = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/submit-review",
        headers=auth_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "under_review"

    done = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/complete",
        headers=auth_headers,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"

    assert InvestigationService.creates_agent_run() is False
    assert InvestigationService.creates_llm_request() is False
    assert InvestigationService.creates_source() is False
    assert InvestigationService.creates_evidence() is False
    assert InvestigationService.creates_verdict() is False


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def test_reject_draft_brief_and_mismatches(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.2 reject")
    draft = client.post(
        f"/projects/{project_id}/briefs",
        json=_brief_body(),
        headers=auth_headers,
    ).json()
    bad = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(draft),
        headers=auth_headers,
    )
    assert bad.status_code == 409
    assert "brief_not_submitted" in _err(bad)

    brief = client.post(
        f"/projects/{project_id}/briefs/{draft['id']}/submit",
        headers=auth_headers,
    ).json()
    assert brief["status"] == "submitted"

    mismatch = client.post(
        f"/projects/{project_id}/investigations",
        json={
            **_create_payload(brief),
            "project_brief_version": brief["version"] + 1,
        },
        headers=auth_headers,
    )
    assert mismatch.status_code == 409
    assert "brief_version_mismatch" in _err(mismatch)

    fp = client.post(
        f"/projects/{project_id}/investigations",
        json={
            **_create_payload(brief),
            "input_fingerprint": "0" * 64,
        },
        headers=auth_headers,
    )
    assert fp.status_code == 409
    assert "fingerprint_mismatch" in _err(fp)


def test_owner_isolation_and_cross_project_brief(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project(client, auth_headers, "P0.2 own1")
    p2 = _project(client, auth_headers, "P0.2 own2")
    brief = _submitted_brief(client, auth_headers, p1)
    cross = client.post(
        f"/projects/{p2}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    )
    assert cross.status_code == 409

    inv = client.post(
        f"/projects/{p1}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    ).json()
    other = client.get(
        f"/projects/{p1}/investigations/{inv['id']}",
        headers=other_auth_headers,
    )
    assert other.status_code == 404


def test_one_active_and_stage_update_immutable_completed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.2 active")
    brief = _submitted_brief(client, auth_headers, project_id)
    inv = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/start",
        headers=auth_headers,
    )

    # second investigation while first active — create is allowed (draft), start is not
    # create OK, but starting would need first not active - create itself checks active
    second = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    )
    assert second.status_code == 409
    assert "active_investigation_exists" in _err(second)

    stage = client.patch(
        f"/projects/{project_id}/investigations/{inv['id']}/stages/market_research",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert stage.status_code == 200
    assert stage.json()["current_stage"] == "market_research"

    client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/complete",
        headers=auth_headers,
    )
    patch_done = client.patch(
        f"/projects/{project_id}/investigations/{inv['id']}",
        json={"blocked_reason": "nope"},
        headers=auth_headers,
    )
    assert patch_done.status_code == 409

    # supersede from completed
    new_inv = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/supersede",
        json=_create_payload(brief),
        headers=auth_headers,
    )
    assert new_inv.status_code == 201, new_inv.text
    assert new_inv.json()["version"] == 2
    assert new_inv.json()["supersedes_investigation_id"] == inv["id"]

    hist = client.get(f"/projects/{project_id}/investigations", headers=auth_headers)
    assert hist.status_code == 200
    by_id = {r["id"]: r for r in hist.json()}
    assert by_id[inv["id"]]["status"] == "superseded"


def test_invalid_transition_and_latest(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.2 trans")
    brief = _submitted_brief(client, auth_headers, project_id)
    inv = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    ).json()
    bad = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/complete",
        headers=auth_headers,
    )
    assert bad.status_code == 409

    latest = client.get(
        f"/projects/{project_id}/investigations/latest",
        headers=auth_headers,
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == inv["id"]

    missing = client.get(
        f"/projects/{uuid4()}/investigations/latest",
        headers=auth_headers,
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_no_agent_llm_rows_from_create(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project(client, auth_headers, "P0.2 sidefx")
    brief = _submitted_brief(client, auth_headers, project_id)
    before_runs = (
        await db_session.execute(select(func.count()).select_from(AgentRunTable))
    ).scalar_one()
    before_llm = (
        await db_session.execute(select(func.count()).select_from(LLMRequestTable))
    ).scalar_one()

    inv = client.post(
        f"/projects/{project_id}/investigations",
        json=_create_payload(brief),
        headers=auth_headers,
    )
    assert inv.status_code == 201
    client.post(
        f"/projects/{project_id}/investigations/{inv.json()['id']}/start",
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

    rows = await db_session.execute(select(InvestigationTable))
    assert len(list(rows.scalars().all())) >= 1

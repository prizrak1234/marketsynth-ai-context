"""Commercial MVP P0.3 — Source domain API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.db.models.llm import LLMRequestTable
from app.db.models.source import SourceTable
from app.services.source_service import SourceService


def _err(resp) -> str:
    body = resp.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def _project(client: TestClient, headers: dict[str, str], name: str = "P0.3 Src") -> str:
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


def _investigation(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    reuse_submitted_brief: bool = False,
) -> dict:
    if reuse_submitted_brief:
        briefs = client.get(
            f"/projects/{project_id}/briefs?status=submitted&limit=1",
            headers=headers,
        )
        assert briefs.status_code == 200
        submitted = briefs.json()[0]
    else:
        created = client.post(
            f"/projects/{project_id}/briefs",
            json=_brief_body(),
            headers=headers,
        )
        assert created.status_code == 201, created.text
        brief = created.json()
        submitted_resp = client.post(
            f"/projects/{project_id}/briefs/{brief['id']}/submit",
            headers=headers,
        )
        assert submitted_resp.status_code == 200, submitted_resp.text
        submitted = submitted_resp.json()
    inv = client.post(
        f"/projects/{project_id}/investigations",
        json={
            "project_brief_id": submitted["id"],
            "project_brief_version": submitted["version"],
            "input_fingerprint": submitted["input_fingerprint"],
        },
        headers=headers,
    )
    assert inv.status_code == 201, inv.text
    return inv.json()


def _source_body(**overrides: object) -> dict:
    body = {
        "source_type": "website",
        "provenance_type": "secondary",
        "title": "Competitor site",
        "origin": "public web",
        "url": "https://Example.COM/path/",
        "publisher": "Example Corp",
        "capabilities": ["webpage", "text"],
        "language": "ru",
        "country": "RU",
    }
    body.update(overrides)
    return body


def test_register_list_attach_reuse_and_side_effects(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers)
    inv = _investigation(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/sources",
        json=_source_body(),
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    src = created.json()
    assert src["status"] == "registered"
    assert src["reliability_level"] == "unverified"
    assert src["version"] == 1
    assert src["domain"] == "example.com"
    assert src["url"] == "https://example.com/path"
    assert "conclusion" not in src["metadata"]
    assert src["metadata"].get("stores_content") is False
    assert SourceService.fetches_external() is False
    assert SourceService.creates_evidence() is False
    assert SourceService.creates_agent_run() is False

    listed = client.get(f"/projects/{project_id}/sources", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # attach to investigation
    link = client.post(
        f"/projects/{project_id}/investigations/{inv['id']}/sources/{src['id']}",
        json={"purpose": "competitor_analysis", "status": "accepted"},
        headers=auth_headers,
    )
    assert link.status_code == 201, link.text

    inv_sources = client.get(
        f"/projects/{project_id}/investigations/{inv['id']}/sources",
        headers=auth_headers,
    )
    assert inv_sources.status_code == 200
    assert len(inv_sources.json()) == 1
    assert inv_sources.json()[0]["source"]["id"] == src["id"]

    # second investigation reuses same source (new inv needs supersede first - create after cancel)
    # reuse within same project via attach only — create another investigation after completing flow:
    # instead cancel not needed: create requires no active - we have draft. Create second source attach.
    # Another investigation: first must not be active. Draft exists - second create while draft OK.
    inv2 = _investigation(client, auth_headers, project_id, reuse_submitted_brief=True)
    reuse = client.post(
        f"/projects/{project_id}/investigations/{inv2['id']}/sources/{src['id']}",
        headers=auth_headers,
    )
    assert reuse.status_code == 201

    # duplicate fingerprint
    dup = client.post(
        f"/projects/{project_id}/sources",
        json=_source_body(),
        headers=auth_headers,
    )
    assert dup.status_code == 409
    assert "duplicate_source" in _err(dup)


def test_supersede_and_reliability_review(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project(client, auth_headers, "P0.3 ver")
    src = client.post(
        f"/projects/{project_id}/sources",
        json=_source_body(title="Report v1", url="https://docs.example/r1"),
        headers=auth_headers,
    ).json()

    reviewed = client.post(
        f"/projects/{project_id}/sources/{src['id']}/review-reliability",
        json={"reliability_level": "medium", "review_note": "looks ok"},
        headers=auth_headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["reliability_level"] == "medium"
    assert reviewed.json()["fingerprint"] == src["fingerprint"]  # identity unchanged

    new = client.post(
        f"/projects/{project_id}/sources/{src['id']}/supersede",
        json=_source_body(
            title="Report v2",
            url="https://docs.example/r1",
            content_hash="abc123",
        ),
        headers=auth_headers,
    )
    assert new.status_code == 201, new.text
    assert new.json()["version"] == 2
    assert new.json()["supersedes_source_id"] == src["id"]
    assert new.json()["reliability_level"] == "unverified"

    old = client.get(
        f"/projects/{project_id}/sources/{src['id']}",
        headers=auth_headers,
    ).json()
    assert old["status"] == "superseded"

    versions = client.get(
        f"/projects/{project_id}/sources/{src['id']}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) >= 2

    snap = client.get(
        f"/projects/{project_id}/sources/{new.json()['id']}/snapshot",
        headers=auth_headers,
    )
    assert snap.status_code == 200
    assert snap.json()["version"] == 2


def test_cross_project_and_owner_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project(client, auth_headers, "P0.3 own1")
    p2 = _project(client, auth_headers, "P0.3 own2")
    src = client.post(
        f"/projects/{p1}/sources",
        json=_source_body(title="Owned", url="https://a.example/x"),
        headers=auth_headers,
    ).json()
    inv2 = _investigation(client, auth_headers, p2)
    cross = client.post(
        f"/projects/{p2}/investigations/{inv2['id']}/sources/{src['id']}",
        headers=auth_headers,
    )
    assert cross.status_code in (404, 409)

    other = client.get(
        f"/projects/{p1}/sources/{src['id']}",
        headers=other_auth_headers,
    )
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_generated_cannot_be_high_and_no_fetch_side_effects(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project(client, auth_headers, "P0.3 gen")
    before_runs = (
        await db_session.execute(select(func.count()).select_from(AgentRunTable))
    ).scalar_one()
    before_llm = (
        await db_session.execute(select(func.count()).select_from(LLMRequestTable))
    ).scalar_one()

    src = client.post(
        f"/projects/{project_id}/sources",
        json=_source_body(
            title="Generated dump",
            url=None,
            provenance_type="generated",
            source_type="internal_document",
            capabilities=["text"],
        ),
        headers=auth_headers,
    ).json()
    bad = client.post(
        f"/projects/{project_id}/sources/{src['id']}/review-reliability",
        json={"reliability_level": "high"},
        headers=auth_headers,
    )
    assert bad.status_code == 409

    after_runs = (
        await db_session.execute(select(func.count()).select_from(AgentRunTable))
    ).scalar_one()
    after_llm = (
        await db_session.execute(select(func.count()).select_from(LLMRequestTable))
    ).scalar_one()
    assert after_runs == before_runs
    assert after_llm == before_llm
    rows = await db_session.execute(select(SourceTable))
    assert len(list(rows.scalars().all())) >= 1

"""Phase 10.1 — campaign plan drafts API."""

from __future__ import annotations

import json

from app.marketing.plan_payload_validation import PLAN_PAYLOAD_MAX_JSON_BYTES
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
    status: str = "active",
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": status},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _agent_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    resp = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist", "name": "Strategist"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _agent_run_id(client: TestClient, headers: dict[str, str], agent_id: str) -> str:
    resp = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "plan"}},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _sample_plan_payload() -> dict:
    return {
        "goal": "Launch summer offer",
        "target_audience": "SMB owners",
        "key_message": "Save time with automation",
        "content_items": [
            {
                "title": "Teaser post",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": "Keep it short",
            },
        ],
    }


def _plan_drafts_url(project_id: str, campaign_id: str) -> str:
    return f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts"


def test_create_list_get_archive_plan_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan drafts P1")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    agent_id = _agent_id(client, auth_headers, project_id)
    run_id = _agent_run_id(client, auth_headers, agent_id)

    created = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={
            "title": "June plan",
            "plan_payload": _sample_plan_payload(),
            "source_agent_run_id": run_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["title"] == "June plan"
    assert draft["status"] == "draft"
    assert draft["source_agent_run_id"] == run_id
    assert draft["plan_payload"]["goal"] == "Launch summer offer"
    assert len(draft["plan_payload"]["content_items"]) == 1

    listed = client.get(_plan_drafts_url(project_id, campaign_id), headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == draft["id"]

    got = client.get(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft['id']}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["id"] == draft["id"]

    archived = client.post(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft['id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    listed_active = client.get(
        _plan_drafts_url(project_id, campaign_id),
        headers=auth_headers,
    )
    assert listed_active.status_code == 200
    assert listed_active.json() == []

    listed_with_archived = client.get(
        _plan_drafts_url(project_id, campaign_id),
        params={"include_archived": True},
        headers=auth_headers,
    )
    assert len(listed_with_archived.json()) == 1


def test_archive_plan_draft_twice_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan archive 409")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=auth_headers,
    ).json()["id"]

    first = client.post(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/archive",
        headers=auth_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/archive",
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_archived_campaign_cannot_create_plan_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan archived campaign")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="draft")
    client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/archive",
        headers=auth_headers,
    )

    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_wrong_campaign_or_project_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, other_auth_headers, "P2")
    c1 = _campaign(client, auth_headers, p1, title="C1")
    c2 = _campaign(client, other_auth_headers, p2, title="C2")

    r = client.post(
        _plan_drafts_url(p1, c2),
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=auth_headers,
    )
    assert r.status_code == 404

    created = client.post(
        _plan_drafts_url(p1, c1),
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=auth_headers,
    ).json()

    r2 = client.get(
        f"{_plan_drafts_url(p1, c1)}/{created['id']}",
        headers=other_auth_headers,
    )
    assert r2.status_code == 404


def test_secret_keys_in_plan_payload_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan secrets")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    payload = _sample_plan_payload()
    payload["api_key"] = "sk-secret"

    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": payload},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_plan_payload_too_large_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan size")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    payload = {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automation",
        "content_items": [
            {
                "title": "Item",
                "channel": "telegram",
                "format": "text",
                "notes": "x" * 400,
            }
            for _ in range(120)
        ],
    }
    assert len(json.dumps(payload).encode("utf-8")) > PLAN_PAYLOAD_MAX_JSON_BYTES

    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": payload},
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_source_agent_run_must_belong_to_owner_project(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, other_auth_headers, "P2")
    c1 = _campaign(client, auth_headers, p1, title="C1")
    other_agent = _agent_id(client, other_auth_headers, p2)
    other_run = _agent_run_id(client, other_auth_headers, other_agent)

    resp = client.post(
        _plan_drafts_url(p1, c1),
        json={
            "title": "Plan",
            "plan_payload": _sample_plan_payload(),
            "source_agent_run_id": other_run,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_create_plan_draft_does_not_create_assets_or_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Plan no side effects")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")

    assets_before = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    jobs_before = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()

    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan only", "plan_payload": _sample_plan_payload()},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    assets_after = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    jobs_after = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()

    assert len(assets_after) == len(assets_before)
    assert len(jobs_after) == len(jobs_before)

    # Sanity: payload stored as structured JSON, not empty
    stored = resp.json()["plan_payload"]
    assert json.dumps(stored)

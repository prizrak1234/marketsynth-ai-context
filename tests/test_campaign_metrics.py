"""Phase 9.3 — campaign operational metrics (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
    status: str = "draft",
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": status},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> None:
    resp = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


def test_project_campaign_metrics_counts_and_flags(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P metrics")
    channel_id = _custom_channel(client, auth_headers, project_id)

    c_active_sched = _campaign(client, auth_headers, project_id, title="A", status="active")
    _campaign(client, auth_headers, project_id, title="B", status="active")
    _campaign(client, auth_headers, project_id, title="C", status="draft")
    _campaign(client, auth_headers, project_id, title="D", status="paused")
    _campaign(client, auth_headers, project_id, title="E", status="completed")

    archived_id = _campaign(client, auth_headers, project_id, title="F", status="draft")
    client.post(
        f"/projects/{project_id}/campaigns/{archived_id}/archive",
        headers=auth_headers,
    )

    # Approved asset for c_active_sched, plus a scheduled job.
    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "asset", "body": "Body", "campaign_id": c_active_sched},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset["id"])

    scheduled_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset["id"], "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    )
    assert job.status_code == 201, job.text

    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    campaigns = body["campaigns"]

    assert campaigns["total"] == 6
    assert campaigns["draft"] == 1
    assert campaigns["active"] == 2
    assert campaigns["paused"] == 1
    assert campaigns["completed"] == 1
    assert campaigns["archived"] == 1

    assert campaigns["active_with_scheduled_jobs"] == 1
    assert campaigns["active_without_approved_assets"] == 1

    lowered = str(body).lower()
    assert "campaign_metadata" not in lowered
    assert "metadata" not in lowered
    assert "body" not in lowered
    assert "channel_config" not in lowered


def test_owner_metrics_aggregate_multiple_projects_and_exclude_others(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, auth_headers, "P2")
    other = _project_id(client, other_auth_headers, "Other")

    _campaign(client, auth_headers, p1, title="A", status="active")
    _campaign(client, auth_headers, p2, title="B", status="draft")
    _campaign(client, other_auth_headers, other, title="C", status="active")

    me = client.get("/me/operational-metrics", headers=auth_headers).json()["campaigns"]
    assert me["total"] == 2
    assert me["active"] == 1
    assert me["draft"] == 1


def test_safe_defaults_when_no_campaigns(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Empty")
    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()["campaigns"]
    assert body == {
        "total": 0,
        "draft": 0,
        "active": 0,
        "paused": 0,
        "completed": 0,
        "archived": 0,
        "active_with_scheduled_jobs": 0,
        "active_without_approved_assets": 0,
    }


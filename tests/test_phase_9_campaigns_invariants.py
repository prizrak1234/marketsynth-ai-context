"""Phase 9.4 — campaigns readiness invariants (freeze guard)."""

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
    status: str,
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": status},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _archive_campaign(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
) -> None:
    resp = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/archive",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


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


def test_invariant_archived_campaign_not_editable_and_not_usable_for_new_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P inv archive")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="draft")
    _archive_campaign(client, auth_headers, project_id, campaign_id)

    # cannot edit archived
    r = client.patch(
        f"/projects/{project_id}/campaigns/{campaign_id}",
        json={"title": "nope"},
        headers=auth_headers,
    )
    assert r.status_code == 409

    # cannot use archived for new assets
    r2 = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert r2.status_code == 409


def test_invariant_campaign_id_must_belong_to_same_project_for_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, auth_headers, "P2")
    other_campaign = _campaign(client, auth_headers, p2, title="C2", status="draft")

    r = client.post(
        f"/projects/{p1}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": other_campaign},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_invariant_job_inherits_campaign_id_from_asset_and_mismatch_is_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P inv inherit")
    c1 = _campaign(client, auth_headers, project_id, title="C1", status="active")
    c2 = _campaign(client, auth_headers, project_id, title="C2", status="active")

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": c1},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset["id"])
    channel_id = _custom_channel(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset["id"], "channel_id": channel_id},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["campaign_id"] == c1

    mismatch = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset["id"], "channel_id": channel_id, "campaign_id": c2},
        headers=auth_headers,
    )
    assert mismatch.status_code == 409


def test_invariant_overview_counts_only_own_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P inv overview")
    c1 = _campaign(client, auth_headers, project_id, title="C1", status="active")
    c2 = _campaign(client, auth_headers, project_id, title="C2", status="active")
    channel_id = _custom_channel(client, auth_headers, project_id)

    asset1 = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": c1},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset1["id"])
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset1["id"], "channel_id": channel_id},
        headers=auth_headers,
    )

    asset2 = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A2", "body": "Body", "campaign_id": c2},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset2["id"])
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset2["id"], "channel_id": channel_id},
        headers=auth_headers,
    )

    ov = client.get(
        f"/projects/{project_id}/campaigns/{c1}/overview",
        headers=auth_headers,
    ).json()
    assert ov["counts"]["assets_total"] == 1
    assert ov["counts"]["jobs_total"] == 1


def test_invariant_metrics_exclude_other_owner_campaigns(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p_other = _project_id(client, other_auth_headers, "P other")
    _campaign(client, auth_headers, p1, title="C1", status="active")
    _campaign(client, other_auth_headers, p_other, title="C2", status="active")

    me = client.get("/me/operational-metrics", headers=auth_headers).json()
    assert me["campaigns"]["total"] == 1


def test_invariant_calendar_campaign_filter_no_body_or_config_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P inv calendar")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="active")
    channel_id = _custom_channel(client, auth_headers, project_id)

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset["id"])
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset["id"],
            "channel_id": channel_id,
            "scheduled_at": (datetime.now(UTC) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z"),
        },
        headers=auth_headers,
    )

    cal = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert cal.status_code == 200, cal.text
    items = cal.json()
    assert items
    sample = items[0]
    raw = str(sample).lower()
    assert "body" not in raw
    assert "channel_config" not in raw


def test_invariant_campaign_endpoints_do_not_expose_versions_or_delivery_logs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P inv endpoints")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="active")

    assets = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/assets",
        headers=auth_headers,
    ).json()
    if assets:
        assert "body" not in assets[0]

    jobs = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    raw = str({"assets": assets, "jobs": jobs}).lower()
    assert "delivery_logs" not in raw
    assert "versions" not in raw


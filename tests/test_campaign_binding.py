"""Phase 9.1 — campaign binding to assets/jobs + calendar."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign_id(client: TestClient, headers: dict[str, str], project_id: str, title: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title},
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


def test_asset_create_with_campaign_and_reject_archived_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P bind asset")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")

    created = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "A1",
            "body": "Body",
            "campaign_id": campaign_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["campaign_id"] == campaign_id

    archived_campaign_id = _campaign_id(client, auth_headers, project_id, "C archived")
    _archive_campaign(client, auth_headers, project_id, archived_campaign_id)
    rejected = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "A2",
            "body": "Body",
            "campaign_id": archived_campaign_id,
        },
        headers=auth_headers,
    )
    assert rejected.status_code == 409


def test_asset_rejects_campaign_from_other_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, auth_headers, "P2")
    campaign_other = _campaign_id(client, auth_headers, p2, "C2")

    r = client.post(
        f"/projects/{p1}/content-assets",
        json={"type": "email", "title": "A", "body": "Body", "campaign_id": campaign_other},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_publication_job_inherits_campaign_id_and_rejects_mismatch(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P bind job")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")
    other_campaign_id = _campaign_id(client, auth_headers, project_id, "C2")

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "A1",
            "body": "Body",
            "campaign_id": campaign_id,
        },
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
    assert created.json()["campaign_id"] == campaign_id

    mismatch = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset["id"],
            "channel_id": channel_id,
            "campaign_id": other_campaign_id,
        },
        headers=auth_headers,
    )
    assert mismatch.status_code == 409


def test_campaign_assets_and_jobs_endpoints_and_calendar_filter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P endpoints")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A1", "body": "Body", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset["id"])
    channel_id = _custom_channel(client, auth_headers, project_id)

    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset["id"], "channel_id": channel_id},
        headers=auth_headers,
    ).json()

    assets = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/assets",
        headers=auth_headers,
    )
    assert assets.status_code == 200, assets.text
    assert len(assets.json()) == 1
    assert assets.json()[0]["id"] == asset["id"]
    assert "body" not in assets.json()[0]

    jobs = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/publication-jobs",
        headers=auth_headers,
    )
    assert jobs.status_code == 200, jobs.text
    assert len(jobs.json()) == 1
    assert jobs.json()[0]["id"] == job["id"]

    cal = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"campaign_id": campaign_id},
        headers=auth_headers,
    )
    assert cal.status_code == 200, cal.text
    items = cal.json()
    assert len(items) >= 1
    sample = items[0]
    assert sample["campaign_id"] == campaign_id
    assert sample["campaign_title"] == "C1"
    assert "channel_config" not in str(sample).lower()
    assert "body" not in str(sample).lower()


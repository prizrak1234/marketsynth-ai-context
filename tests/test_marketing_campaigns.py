"""Phase 9.0 — marketing campaigns skeleton (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _brief_id(client: TestClient, headers: dict[str, str], project_id: str, title: str) -> str:
    return client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={
            "title": title,
            "product_description": "pd",
            "target_audience": "ta",
            "offer": "offer",
            "goals": ["g"],
            "constraints": {},
        },
        headers=headers,
    ).json()["id"]


def test_create_list_get_patch_archive_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Campaigns P1")
    brief_id = _brief_id(client, auth_headers, project_id, "Brief 1")

    start_at = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    end_at = (datetime.now(UTC) + timedelta(days=2)).isoformat().replace("+00:00", "Z")

    created = client.post(
        f"/projects/{project_id}/campaigns",
        json={
            "brief_id": brief_id,
            "title": "Campaign 1",
            "description": "Desc",
            "status": "draft",
            "start_at": start_at,
            "end_at": end_at,
            "campaign_metadata": {"k": "v"},
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    campaign = created.json()
    assert campaign["title"] == "Campaign 1"
    assert campaign["brief_id"] == brief_id
    assert campaign["campaign_metadata"]["k"] == "v"

    listed = client.get(f"/projects/{project_id}/campaigns", headers=auth_headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == campaign["id"]

    got = client.get(
        f"/projects/{project_id}/campaigns/{campaign['id']}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["id"] == campaign["id"]

    patched = client.patch(
        f"/projects/{project_id}/campaigns/{campaign['id']}",
        json={
            "title": "Campaign 1 updated",
            "status": "active",
            "campaign_metadata": {"x": 1},
        },
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    updated = patched.json()
    assert updated["title"] == "Campaign 1 updated"
    assert updated["status"] == "active"
    assert updated["campaign_metadata"]["x"] == 1

    archived = client.post(
        f"/projects/{project_id}/campaigns/{campaign['id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


def test_owner_project_scope_other_project_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Campaigns P1")
    other_project_id = _project_id(client, other_auth_headers, "Campaigns P2")
    brief_id = _brief_id(client, auth_headers, project_id, "Brief")

    created = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign", "brief_id": brief_id},
        headers=auth_headers,
    ).json()

    # other owner cannot read
    r = client.get(
        f"/projects/{project_id}/campaigns/{created['id']}",
        headers=other_auth_headers,
    )
    assert r.status_code == 404

    # cannot create against someone else's project
    r2 = client.post(
        f"/projects/{other_project_id}/campaigns",
        json={"title": "Nope"},
        headers=auth_headers,
    )
    assert r2.status_code == 404


def test_brief_must_belong_to_same_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1")
    p2 = _project_id(client, auth_headers, "P2")
    brief_other = _brief_id(client, auth_headers, p2, "Brief other")

    r = client.post(
        f"/projects/{p1}/campaigns",
        json={"title": "Campaign", "brief_id": brief_other},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_naive_start_end_rejected_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P naive")
    r = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign", "start_at": "2026-06-03T10:00:00"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_end_at_must_be_greater_than_start_at_422_on_create_and_409_on_patch(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P bounds")
    start = (datetime.now(UTC) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    end = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    r = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign", "start_at": start, "end_at": end},
        headers=auth_headers,
    )
    assert r.status_code == 422

    created = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign", "start_at": start},
        headers=auth_headers,
    ).json()

    r2 = client.patch(
        f"/projects/{project_id}/campaigns/{created['id']}",
        json={"end_at": (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")},
        headers=auth_headers,
    )
    assert r2.status_code == 409


def test_archived_campaign_cannot_be_edited_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P archived")
    created = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Campaign"},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/campaigns/{created['id']}/archive",
        headers=auth_headers,
    )

    r = client.patch(
        f"/projects/{project_id}/campaigns/{created['id']}",
        json={"title": "nope"},
        headers=auth_headers,
    )
    assert r.status_code == 409


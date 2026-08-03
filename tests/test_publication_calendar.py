"""Phase 8.1 — publication calendar read model (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Calendar"},
        headers=headers,
    ).json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": title, "body": "Body"},
        headers=headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    return asset_id


def _custom_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    name: str,
) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": name, "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


def test_calendar_lists_scheduled_jobs_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C1")
    asset_id = _approve_asset(client, auth_headers, project_id, title="A1")

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()

    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    ).json()
    assert any(item["job_id"] == job["id"] for item in items)
    first = next(item for item in items if item["job_id"] == job["id"])
    assert first["asset_title"] == "A1"
    assert first["channel_name"] == "C1"
    assert first["status"] == "scheduled"
    assert "channel_config" not in first
    assert "body" not in first


def test_calendar_filters_by_date_range(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C1")
    asset_id = _approve_asset(client, auth_headers, project_id, title="A1")

    in_window = (datetime.now(UTC) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    out_window = (datetime.now(UTC) + timedelta(days=3)).isoformat().replace("+00:00", "Z")
    job_in = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": in_window},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": out_window},
        headers=auth_headers,
    )

    from_at = (datetime.now(UTC) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    to_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"from_at": from_at, "to_at": to_at},
        headers=auth_headers,
    ).json()
    ids = {item["job_id"] for item in items}
    assert job_in in ids
    assert len(ids) == 1


def test_calendar_filters_by_channel_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    ch1 = _custom_channel(client, auth_headers, project_id, name="C1")
    ch2 = _custom_channel(client, auth_headers, project_id, name="C2")
    asset_id = _approve_asset(client, auth_headers, project_id, title="A1")
    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    job1 = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": ch1, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": ch2, "scheduled_at": scheduled_at},
        headers=auth_headers,
    )

    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"channel_id": ch1},
        headers=auth_headers,
    ).json()
    assert {item["job_id"] for item in items} == {job1}


def test_calendar_filters_by_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C1")
    asset_id = _approve_asset(client, auth_headers, project_id, title="A1")
    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()["id"]

    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"status": "scheduled"},
        headers=auth_headers,
    ).json()
    assert {item["job_id"] for item in items} == {job}


def test_calendar_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.parametrize("param", ["from_at", "to_at"])
def test_calendar_rejects_naive_datetimes(
    client: TestClient,
    auth_headers: dict[str, str],
    param: str,
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={param: "2026-06-03T15:00:00"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_calendar_default_statuses_do_not_show_terminal_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create an unsupported job (email channel) which will fail on process.
    project_id = _project_id(client, auth_headers)
    channel_id = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Email", "type": "email", "config": {"smtp_host": "smtp.example.com"}},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _approve_asset(client, auth_headers, project_id, title="A1")
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    )
    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "failed"

    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    ).json()
    ids = {item["job_id"] for item in items}
    assert job_id not in ids


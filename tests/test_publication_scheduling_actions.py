"""Phase 8.2 — reschedule/cancel scheduled publication jobs (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.models.publishing import PublicationJobTable
from app.publishing.contracts import PublicationJobStatus
from app.services.publication_scheduler_service import PublicationSchedulerService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Scheduling actions"},
        headers=headers,
    ).json()["id"]


def _approve_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "A", "body": "Body"},
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


def _channel_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


def _create_scheduled_job(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = _approve_asset(client, headers, project_id)
    channel_id = _channel_id(client, headers, project_id)
    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    return client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=headers,
    ).json()["id"]


def test_reschedule_scheduled_job_success(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    new_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/reschedule",
        json={"scheduled_at": new_time},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    job = response.json()
    assert job["status"] == "scheduled"
    assert job["queued_at"] is None


def test_reschedule_naive_datetime_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/reschedule",
        json={"scheduled_at": "2026-06-04T15:00:00"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_reschedule_past_datetime_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/reschedule",
        json={"scheduled_at": past},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("status", ["queued", "running", "succeeded", "failed", "cancelled"])
@pytest.mark.asyncio
async def test_reschedule_non_scheduled_409(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    status: str,
) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    row = await db_session.get(PublicationJobTable, UUID(job_id))
    assert row is not None
    row.status = PublicationJobStatus(status)
    db_session.add(row)
    await db_session.commit()

    new_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/reschedule",
        json={"scheduled_at": new_time},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_cancel_scheduled_job_success(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"


@pytest.mark.parametrize("status", ["running", "succeeded", "failed", "cancelled"])
@pytest.mark.asyncio
async def test_cancel_non_scheduled_409(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    status: str,
) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    row = await db_session.get(PublicationJobTable, UUID(job_id))
    assert row is not None
    row.status = PublicationJobStatus(status)
    db_session.add(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_other_owner_cannot_reschedule_or_cancel(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    new_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    res = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/reschedule",
        json={"scheduled_at": new_time},
        headers=other_auth_headers,
    )
    assert res.status_code == 404

    cancel = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=other_auth_headers,
    )
    assert cancel.status_code == 404


@pytest.mark.asyncio
async def test_cancelled_scheduled_job_not_released(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)

    client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )

    # Even if scheduled_at is due, cancelled job must not be released.
    row = await db_session.get(PublicationJobTable, UUID(job_id))
    assert row is not None
    row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(row)
    await db_session.commit()

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0
    updated = await db_session.get(PublicationJobTable, UUID(job_id))
    assert updated is not None
    assert updated.status == PublicationJobStatus.CANCELLED


def test_cancelled_scheduled_job_not_in_default_calendar(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    job_id = _create_scheduled_job(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )

    items = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    ).json()
    ids = {item["job_id"] for item in items}
    assert job_id not in ids


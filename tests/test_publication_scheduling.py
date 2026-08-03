"""Phase 8.0 — scheduled publication jobs (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.publishing.contracts import PublicationJobStatus
from app.services.publication_scheduler_service import PublicationSchedulerService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Scheduling"},
        headers=headers,
    ).json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    body: str = "Body",
) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Scheduled", "body": body},
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


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


def _email_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Email", "type": "email", "config": {"smtp_host": "smtp.example.com"}},
        headers=headers,
    ).json()["id"]


def test_create_job_without_scheduled_at_is_queued_and_sets_queued_at(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["queued_at"] is not None
    assert job["scheduled_at"] is None


def test_create_job_with_future_scheduled_at_is_scheduled(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["status"] == "scheduled"
    assert job["scheduled_at"] is not None
    assert job["queued_at"] is None


def test_naive_datetime_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset_id,
            "channel_id": channel_id,
            "scheduled_at": "2026-06-03T15:00:00",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_past_datetime_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": past},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_due_scheduled_job_released_to_queued(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    row = await db_session.get(PublicationJobTable, job_id)
    assert row is not None
    row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(row)
    await db_session.commit()

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 1

    updated = await db_session.get(PublicationJobTable, job_id)
    assert updated is not None
    assert updated.status == PublicationJobStatus.QUEUED
    assert updated.queued_at is not None


@pytest.mark.asyncio
async def test_future_scheduled_job_not_released(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0
    updated = await db_session.get(PublicationJobTable, job_id)
    assert updated is not None
    assert updated.status == PublicationJobStatus.SCHEDULED


@pytest.mark.asyncio
async def test_inactive_channel_fails_release(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    # Make due
    row = await db_session.get(PublicationJobTable, job_id)
    assert row is not None
    row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(row)
    await db_session.commit()

    # Pause channel
    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0
    updated = await db_session.get(PublicationJobTable, job_id)
    assert updated is not None
    assert updated.status == PublicationJobStatus.FAILED
    assert updated.error == "scheduled_job_channel_not_active"


@pytest.mark.asyncio
async def test_asset_not_approved_fails_release(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    # Make due
    row = await db_session.get(PublicationJobTable, job_id)
    assert row is not None
    row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(row)
    await db_session.commit()

    # Downgrade asset to draft
    repo = ContentAssetRepository(db_session)
    asset = await repo.get_for_project(UUID(asset_id), UUID(created["owner_id"]), UUID(project_id))
    assert asset is not None
    from app.marketing.contracts import ContentAssetStatus

    asset.status = ContentAssetStatus.DRAFT
    await repo.update(asset)
    await db_session.commit()

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0
    updated = await db_session.get(PublicationJobTable, job_id)
    assert updated is not None
    assert updated.status == PublicationJobStatus.FAILED
    assert updated.error == "scheduled_job_asset_not_approved"


@pytest.mark.asyncio
async def test_version_mismatch_fails_release(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    # Make due
    row = await db_session.get(PublicationJobTable, job_id)
    assert row is not None
    row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(row)
    await db_session.commit()

    # Mutate job pinned version to mismatch approved_version_number
    row2 = await db_session.get(PublicationJobTable, job_id)
    assert row2 is not None
    row2.asset_version_number += 1
    db_session.add(row2)
    await db_session.commit()

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0
    updated = await db_session.get(PublicationJobTable, job_id)
    assert updated is not None
    assert updated.status == PublicationJobStatus.FAILED
    assert updated.error == "scheduled_job_version_mismatch"


def test_replay_scheduled_job_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _custom_channel(client, auth_headers, project_id)

    scheduled_at = (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id, "scheduled_at": scheduled_at},
        headers=auth_headers,
    ).json()
    job_id = created["id"]

    replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 409


def test_worker_calls_release_due_jobs_before_processing_queued(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _approve_asset(client, auth_headers, project_id)
    channel_id = _email_channel(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )

    with patch(
        "app.services.publication_job_processor.PublicationSchedulerService.release_due_jobs",
        new_callable=AsyncMock,
        return_value=0,
    ) as mock_release:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        assert mock_release.await_count >= 1


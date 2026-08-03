"""Phase 8.4 — scheduling readiness invariants (freeze guard).

No new features here: this file locks the expected behavior for Phase 8.x.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.services.publication_job_processor import PublicationJobProcessor
from app.services.publication_scheduler_service import PublicationSchedulerService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _draft_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
) -> str:
    return client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": title, "body": "body"},
        headers=headers,
    ).json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _custom_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    name: str,
) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": name, "type": "custom", "config": {"secret": "must_not_leak"}},
        headers=headers,
    ).json()["id"]


def _create_scheduled_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
    scheduled_at: datetime,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset_id,
            "channel_id": channel_id,
            "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invariant_naive_datetime_rejected_for_create_and_reschedule_and_calendar(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Phase 8 invariants")
    asset_id = _draft_asset(client, auth_headers, project_id, title="A")
    _approve_asset(client, auth_headers, project_id, asset_id)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C")

    # create (naive) -> 422
    r1 = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset_id,
            "channel_id": channel_id,
            "scheduled_at": "2026-06-03T15:00:00",
        },
        headers=auth_headers,
    )
    assert r1.status_code == 422

    # reschedule (naive) -> 422
    created = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    r2 = client.post(
        f"/projects/{project_id}/publication-jobs/{created['id']}/reschedule",
        json={"scheduled_at": "2026-06-03T15:00:00"},
        headers=auth_headers,
    )
    assert r2.status_code == 422

    # calendar (naive bounds) -> 422
    r3 = client.get(
        f"/projects/{project_id}/publication-calendar",
        params={"from_at": "2026-06-03T00:00:00"},
        headers=auth_headers,
    )
    assert r3.status_code == 422


def test_invariant_scheduled_jobs_are_not_replayable(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Phase 8 replay")
    asset_id = _draft_asset(client, auth_headers, project_id, title="A")
    _approve_asset(client, auth_headers, project_id, asset_id)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C")

    created = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    replay = client.post(
        f"/projects/{project_id}/publication-jobs/{created['id']}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 409


@pytest.mark.asyncio
async def test_invariant_release_does_not_touch_future_jobs_and_cancelled_not_released(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "Phase 8 release")
    asset_id = _draft_asset(client, auth_headers, project_id, title="A")
    _approve_asset(client, auth_headers, project_id, asset_id)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C")

    future = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    cancelled = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    client.post(
        f"/projects/{project_id}/publication-jobs/{cancelled['id']}/cancel",
        headers=auth_headers,
    )

    released = await PublicationSchedulerService(db_session).release_due_jobs(now=datetime.now(UTC))
    assert released == 0

    row_future = await db_session.get(PublicationJobTable, UUID(future["id"]))
    row_cancelled = await db_session.get(PublicationJobTable, UUID(cancelled["id"]))
    assert row_future is not None
    assert row_cancelled is not None
    assert row_future.status.value == "scheduled"
    assert row_cancelled.status.value == "cancelled"


@pytest.mark.asyncio
async def test_invariant_approved_only_and_pinned_version_not_weakened(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "Phase 8 pin")
    channel_id = _custom_channel(client, auth_headers, project_id, name="C")
    asset_id = _draft_asset(client, auth_headers, project_id, title="A")

    # draft asset -> cannot schedule
    r = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset_id,
            "channel_id": channel_id,
            "scheduled_at": (datetime.now(UTC) + timedelta(minutes=10))
            .isoformat()
            .replace("+00:00", "Z"),
        },
        headers=auth_headers,
    )
    assert r.status_code == 409

    approved = _approve_asset(client, auth_headers, project_id, asset_id)
    pinned = int(approved["approved_version_number"])

    scheduled = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    assert scheduled["asset_version_number"] == pinned

    # Mutate "current" version to simulate later drafts; job must remain pinned.
    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(asset_id),
        UUID(approved["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.current_version_number = pinned + 1
    await repo.update(row)
    await db_session.commit()

    fetched = client.get(
        f"/projects/{project_id}/publication-jobs/{scheduled['id']}",
        headers=auth_headers,
    ).json()
    assert fetched["asset_version_number"] == pinned


def test_invariant_calendar_and_metrics_do_not_expose_body_config_or_logs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Phase 8 exposure")
    asset_id = _draft_asset(client, auth_headers, project_id, title="A")
    _approve_asset(client, auth_headers, project_id, asset_id)
    channel_id = _custom_channel(client, auth_headers, project_id, name="C")

    _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    calendar = client.get(
        f"/projects/{project_id}/publication-calendar",
        headers=auth_headers,
    )
    assert calendar.status_code == 200, calendar.text
    items = calendar.json()
    assert isinstance(items, list)
    if items:
        sample = items[0]
        # must not include asset body, channel config, or any delivery log payloads
        forbidden_keys = {
            "body",
            "asset_body",
            "channel_config",
            "request",
            "response",
            "delivery_logs",
        }
        assert not (set(sample.keys()) & forbidden_keys)

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    )
    assert metrics.status_code == 200, metrics.text
    raw = metrics.json()
    raw_str = str(raw).lower()
    assert "channel_config" not in raw_str
    assert "must_not_leak" not in raw_str
    assert "body" not in raw_str


@pytest.mark.asyncio
async def test_invariant_worker_calls_release_before_listing_queued(
    db_session: AsyncSession,
) -> None:
    """Lock call ordering: release_due_jobs must happen before draining queued jobs."""

    released_flag = {"done": False}

    async def _release_due_jobs(*args, **kwargs) -> int:  # noqa: ANN001
        released_flag["done"] = True
        return 0

    async def _list_queued(self, *args, **kwargs):  # noqa: ANN001
        assert released_flag["done"] is True
        return []

    with patch.object(
        PublicationSchedulerService,
        "release_due_jobs",
        new=AsyncMock(side_effect=_release_due_jobs),
    ), patch.object(
        PublicationJobRepository,
        "list_queued",
        new=_list_queued,
    ):
        processor = PublicationJobProcessor(db_session)
        result = await processor.process_batch(limit=1)
        assert result.processed_count == 0


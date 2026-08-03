"""Phase 8.3 — scheduling operational metrics (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.models.publishing import PublicationJobTable
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post(
        "/projects",
        json={"name": name},
        headers=headers,
    ).json()["id"]


def _approve_asset(client: TestClient, headers: dict[str, str], project_id: str, title: str) -> str:
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


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str, name: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": name, "type": "custom", "config": {}},
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
) -> str:
    return client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset_id,
            "channel_id": channel_id,
            "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    ).json()["id"]


@pytest.mark.asyncio
async def test_project_metrics_scheduled_due_next_cancelled(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "Metrics P1")
    asset_id = _approve_asset(client, auth_headers, project_id, "A1")
    channel_id = _custom_channel(client, auth_headers, project_id, "C1")

    now = datetime.now(UTC)
    due_id = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=now + timedelta(minutes=5),
    )
    _next_id = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=now + timedelta(hours=2),
    )
    cancel_id = _create_scheduled_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=now + timedelta(hours=3),
    )

    # Make one scheduled job due.
    row = await db_session.get(PublicationJobTable, UUID(due_id))
    assert row is not None
    row.scheduled_at = now - timedelta(minutes=1)
    db_session.add(row)
    await db_session.commit()

    # Cancel one scheduled job (counts in last 24h).
    client.post(
        f"/projects/{project_id}/publication-jobs/{cancel_id}/cancel",
        headers=auth_headers,
    )

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    publishing = metrics["publishing"]
    assert publishing["scheduled_jobs_count"] == 2  # due + next (cancelled excluded)
    assert publishing["due_scheduled_jobs_count"] == 1
    assert publishing["next_scheduled_publication_at"] is not None
    assert publishing["cancelled_scheduled_jobs_24h"] == 1

    # next_scheduled_publication_at should be the nearest future scheduled time.
    expected_prefix = (now + timedelta(hours=2)).isoformat()[:16]
    assert str(publishing["next_scheduled_publication_at"]).startswith(expected_prefix)


@pytest.mark.asyncio
async def test_owner_metrics_aggregate_multiple_projects_and_exclude_others(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "Owner metrics P1")
    p2 = _project_id(client, auth_headers, "Owner metrics P2")
    other_project = _project_id(client, other_auth_headers, "Other owner P")

    now = datetime.now(UTC)
    for project_id in (p1, p2):
        asset_id = _approve_asset(client, auth_headers, project_id, "A")
        channel_id = _custom_channel(client, auth_headers, project_id, "C")
        _create_scheduled_job(
            client,
            auth_headers,
            project_id,
            asset_id=asset_id,
            channel_id=channel_id,
            scheduled_at=now + timedelta(minutes=10),
        )

    # Other owner's scheduled job must not be included.
    asset_other = _approve_asset(client, other_auth_headers, other_project, "AO")
    channel_other = _custom_channel(client, other_auth_headers, other_project, "CO")
    _create_scheduled_job(
        client,
        other_auth_headers,
        other_project,
        asset_id=asset_other,
        channel_id=channel_other,
        scheduled_at=now + timedelta(minutes=10),
    )

    me_metrics = client.get(
        "/me/operational-metrics",
        headers=auth_headers,
    ).json()
    publishing = me_metrics["publishing"]
    assert publishing["scheduled_jobs_count"] == 2


def test_metrics_safe_defaults_when_no_scheduled_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Empty schedule")
    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    publishing = metrics["publishing"]
    assert publishing["scheduled_jobs_count"] == 0
    assert publishing["due_scheduled_jobs_count"] == 0
    assert publishing["next_scheduled_publication_at"] is None
    assert publishing["cancelled_scheduled_jobs_24h"] == 0


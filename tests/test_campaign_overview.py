"""Phase 9.2 — campaign overview read model (freeze guard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.models.publication_delivery_log import PublicationDeliveryLogTable
from app.publishing.contracts import PublicationDeliveryLogStatus, PublishingChannelType
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign_id(client: TestClient, headers: dict[str, str], project_id: str, title: str) -> str:
    resp = client.post(f"/projects/{project_id}/campaigns", json={"title": title}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


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


def test_overview_empty_campaign(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P empty overview")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")

    resp = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["campaign"]["id"] == campaign_id
    assert body["counts"]["assets_total"] == 0
    assert body["counts"]["jobs_total"] == 0
    assert body["schedule"]["next_scheduled_publication_at"] is None
    assert body["schedule"]["last_successful_publication_at"] is None
    assert body["recent_jobs"] == []


@pytest.mark.asyncio
async def test_overview_counts_assets_and_jobs_and_schedule(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P overview")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")
    channel_id = _custom_channel(client, auth_headers, project_id)

    # Assets: draft / approved / archived
    client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "draft", "body": "b", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    a_approved = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "approved", "body": "b", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, a_approved["id"])
    a_archived = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "arch", "body": "b", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    client.delete(
        f"/projects/{project_id}/content-assets/{a_archived['id']}",
        headers=auth_headers,
    )

    # Jobs: create a scheduled and a queued (from campaign-bound approved asset)
    future = (datetime.now(UTC) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": a_approved["id"], "channel_id": channel_id, "scheduled_at": future},
        headers=auth_headers,
    ).json()

    queued = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": a_approved["id"], "channel_id": channel_id},
        headers=auth_headers,
    ).json()

    # Create a successful delivery log for queued job so last_successful_publication_at is set.
    row = PublicationDeliveryLogTable(
        owner_id=UUID(queued["owner_id"]),
        project_id=UUID(project_id),
        publication_job_id=UUID(queued["id"]),
        channel_id=UUID(channel_id),
        channel_type=PublishingChannelType.CUSTOM,
        status=PublicationDeliveryLogStatus.SUCCEEDED,
        attempt_number=1,
        duration_ms=10,
        error_code=None,
        error_message=None,
        response_preview="ok",
    )
    db_session.add(row)
    await db_session.commit()

    resp = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["counts"]["assets_total"] == 3
    assert body["counts"]["assets_draft"] == 1
    assert body["counts"]["assets_approved"] == 1
    assert body["counts"]["assets_archived"] == 1

    assert body["counts"]["jobs_total"] >= 2
    assert body["counts"]["jobs_scheduled"] >= 1
    assert body["counts"]["jobs_queued"] >= 1

    assert body["schedule"]["next_scheduled_publication_at"] is not None
    assert body["schedule"]["last_successful_publication_at"] is not None

    # No leaks
    lowered = str(body).lower()
    assert "channel_config" not in lowered
    assert "delivery_logs" not in lowered
    assert "asset_versions" not in lowered
    assert "body" not in lowered


@pytest.mark.asyncio
async def test_recent_jobs_limit_10(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P recent limit")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")
    channel_id = _custom_channel(client, auth_headers, project_id)

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "approved", "body": "b", "campaign_id": campaign_id},
        headers=auth_headers,
    ).json()
    _approve_asset(client, auth_headers, project_id, asset["id"])

    # Create 12 jobs, then force campaign_id (should already inherit) and created_at order.
    created_ids: list[str] = []
    for _ in range(12):
        job = client.post(
            f"/projects/{project_id}/publication-jobs",
            json={"asset_id": asset["id"], "channel_id": channel_id},
            headers=auth_headers,
        ).json()
        created_ids.append(job["id"])

    resp = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    recent = resp.json()["recent_jobs"]
    assert len(recent) == 10


def test_overview_scope_other_owner_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P scope")
    campaign_id = _campaign_id(client, auth_headers, project_id, "C1")

    r = client.get(
        f"/projects/{project_id}/campaigns/{campaign_id}/overview",
        headers=other_auth_headers,
    )
    assert r.status_code == 404


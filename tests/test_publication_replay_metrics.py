"""Phase 6.3 — publication replay and operational metrics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES, get_agent_tool_matrix
from app.db.repositories.content_assets import ContentAssetRepository
from app.publishing.contracts import PublicationJobStatus
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Replay metrics"},
        headers=headers,
    ).json()["id"]


def _webhook_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    status: str = "active",
) -> str:
    channel = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={
            "name": "Hook",
            "type": "webhook",
            "config": {"url": "https://example.com/publish"},
        },
        headers=headers,
    ).json()["id"]
    if status != "active":
        client.patch(
            f"/projects/{project_id}/publishing-channels/{channel}",
            json={"status": status},
            headers=headers,
        )
    return channel


def _approve_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Replay", "body": "body"},
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


def _queue_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
) -> str:
    return client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=headers,
    ).json()["id"]


def _fail_job_via_webhook(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    job_id: str,
) -> None:
    mock_response = httpx.Response(
        500,
        request=httpx.Request("POST", "https://example.com/publish"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        for _ in range(3):
            client.post(
                f"/projects/{project_id}/publication-jobs/process",
                headers=headers,
            )


def test_failed_job_replay_to_queued(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)

    replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 200
    body = replay.json()
    assert body["status"] == "queued"
    assert body["attempts"] == 0
    assert body["error"] is None
    assert body["started_at"] is None
    assert body["finished_at"] is None


def test_cancelled_job_can_be_replayed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )
    replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "queued"


def test_succeeded_job_cannot_replay(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    mock_ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_ok):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_queued_job_cannot_replay(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_running_job_cannot_replay(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.db.models.publishing import PublicationJobTable

    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    row = await db_session.get(PublicationJobTable, UUID(job_id))
    assert row is not None
    row.status = PublicationJobStatus.RUNNING
    db_session.add(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_inactive_channel_blocks_replay(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)
    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_missing_asset_blocks_replay(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    owner_id = UUID(job["owner_id"])
    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(UUID(asset_id), owner_id, UUID(project_id))
    assert row is not None
    await db_session.delete(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_approved_version_mismatch_blocks_replay(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(asset_id),
        UUID(job["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.approved_version_number = (row.approved_version_number or 1) + 1
    await repo.update(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_batch_replay_resets_failed_jobs(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)

    batch = client.post(
        f"/projects/{project_id}/publication-jobs/replay-batch",
        json={"statuses": ["failed"], "limit": 50},
        headers=auth_headers,
    )
    assert batch.status_code == 200
    body = batch.json()
    assert body["matched_count"] >= 1
    assert body["replayed_count"] >= 1

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "queued"


def test_batch_replay_skips_succeeded(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    mock_ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_ok):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    batch = client.post(
        f"/projects/{project_id}/publication-jobs/replay-batch",
        json={"statuses": ["failed"], "limit": 50},
        headers=auth_headers,
    ).json()
    assert batch["replayed_count"] == 0

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "succeeded"


def test_batch_replay_limit_max_100(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/publication-jobs/replay-batch",
        json={"statuses": ["failed"], "limit": 101},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_metrics_count_jobs_and_deliveries(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    mock_ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_ok):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    publishing = metrics["publishing"]
    assert "jobs_by_status" in publishing
    assert publishing["jobs_by_status"].get("succeeded", 0) >= 1
    assert "deliveries_by_status" in publishing
    assert publishing["deliveries_by_status"].get("succeeded", 0) >= 1
    assert "failed_jobs_count" in publishing
    assert "failed_count_by_channel_id" in publishing
    assert isinstance(publishing["failed_count_by_channel_id"], dict)

    owner_metrics = client.get("/me/operational-metrics", headers=auth_headers).json()
    assert "publishing" in owner_metrics


def test_health_pending_publication_jobs_count(client: TestClient) -> None:
    response = client.get("/health/operations")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "pending_publication_jobs_count" in body
    assert "publication_worker_enabled" in body


def test_replay_does_not_auto_dispatch(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    _fail_job_via_webhook(client, auth_headers, project_id, job_id)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        replay = client.post(
            f"/projects/{project_id}/publication-jobs/{job_id}/replay",
            headers=auth_headers,
        )
        mock_post.assert_not_called()
    assert replay.json()["status"] == "queued"


def test_agent_tool_matrix_unchanged() -> None:
    matrix = get_agent_tool_matrix()
    assert "copywriter" in matrix
    names = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in names

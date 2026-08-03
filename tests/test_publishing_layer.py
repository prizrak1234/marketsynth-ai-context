"""Phase 6.0 — publishing channels and publication jobs (HTTP-only, no dispatch)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES, get_agent_tool_matrix
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.publishing.contracts import PublicationJobStatus
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Publishing layer"},
        headers=headers,
    ).json()["id"]


def _create_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    name: str = "Custom main",
    channel_type: str = "custom",
    config: dict | None = None,
) -> dict:
    payload = {
        "name": name,
        "type": channel_type,
        "config": config or {},
    }
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_draft_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Newsletter", "body": "Hello"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


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
    assert response.status_code == 200
    return response.json()


def test_create_publishing_channel(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    body = _create_channel(client, auth_headers, project_id)
    assert body["name"] == "Custom main"
    assert body["type"] == "custom"
    assert body["status"] == "active"
    assert "config_preview" in body
    assert "channel_config" not in body


def test_list_channels_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    _create_channel(client, auth_headers, project_id)

    other_list = client.get(
        f"/projects/{project_id}/publishing-channels",
        headers=other_auth_headers,
    )
    assert other_list.status_code == 404


def test_channel_config_secret_not_returned(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel = _create_channel(
        client,
        auth_headers,
        project_id,
        config={"api_key": "super-secret", "webhook_url": "https://example.com/hook"},
    )
    preview = channel["config_preview"]
    assert preview.get("api_key") == "***"
    assert "super-secret" not in str(preview)


def test_pause_and_archive_channel(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]

    paused = client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    archived = client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "archived"},
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_create_publication_job_for_approved_asset(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    approved = _approve_asset(client, auth_headers, project_id, asset_id)

    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "queued"
    assert job["asset_version_number"] == approved["approved_version_number"]
    assert job["payload_preview"]["asset_id"] == asset_id


def test_cannot_create_job_for_draft_asset(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cannot_create_job_without_approved_version_number(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    approved = _approve_asset(client, auth_headers, project_id, asset_id)

    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(asset_id),
        UUID(approved["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.approved_version_number = None
    await repo.update(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_cannot_create_job_for_paused_or_archived_channel(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)

    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )
    paused_job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert paused_job.status_code == 409

    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "active"},
        headers=auth_headers,
    )
    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "archived"},
        headers=auth_headers,
    )
    archived_job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert archived_job.status_code == 409


@pytest.mark.asyncio
async def test_job_stores_approved_version_not_current(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    approved = _approve_asset(client, auth_headers, project_id, asset_id)
    approved_version = approved["approved_version_number"]

    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(asset_id),
        UUID(approved["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.current_version_number = approved_version + 1
    await repo.update(row)
    await db_session.commit()

    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert job.status_code == 201
    assert job.json()["asset_version_number"] == approved_version


def test_cancel_queued_job(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)

    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()
    job_id = created["id"]

    cancelled = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/cancel",
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["finished_at"] is not None


@pytest.mark.asyncio
async def test_cannot_cancel_succeeded_job(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)

    created = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()
    job_id = UUID(created["id"])

    row = await db_session.get(PublicationJobTable, job_id)
    assert row is not None
    row.status = PublicationJobStatus.SUCCEEDED
    db_session.add(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publication-jobs/{str(job_id)}/cancel",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_publication_jobs_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_channel(client, auth_headers, project_id)["id"]
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()

    other_get = client.get(
        f"/projects/{project_id}/publication-jobs/{job['id']}",
        headers=other_auth_headers,
    )
    assert other_get.status_code == 404


def test_agent_tool_matrix_unchanged() -> None:
    matrix = get_agent_tool_matrix()
    assert "orchestrator" in matrix
    assert "copywriter" in matrix
    for entry in matrix.values():
        assert "read" in entry
        assert "write" in entry


def test_no_publication_agent_tools_in_registry() -> None:
    registry = get_tool_registry()
    names = {tool.name for tool in registry.list_registered()}
    publication_related = {name for name in names if "publish" in name or "publication" in name}
    assert publication_related == set()
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in names

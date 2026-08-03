"""Phase AI.56 — Media generation abstraction (mock only, no external API)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_generation_jobs import MediaGenerationJobRepository
from app.marketing.media_contracts import MediaAssetStatus, MediaBriefStatus
from app.media_generation.contracts import MediaGenerationJobStatus, MediaGenerationProvider
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.56 Gen"}, headers=headers).json()["id"]


def _approved_brief(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = approved_content_asset_id(client, headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, headers, project_id, brief_id)
    return brief_id


def test_draft_brief_cannot_create_generation_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    ).json()["media_brief_id"]
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_openai_provider_blocked_when_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = _approved_brief(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "openai_images"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_mock_job_lifecycle(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = _approved_brief(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["status"] == MediaGenerationJobStatus.QUEUED.value
    assert created.json()["provider"] == MediaGenerationProvider.MOCK.value

    started = client.post(
        f"/projects/{project_id}/media-generation-jobs/{job_id}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    assert started.json()["status"] == MediaGenerationJobStatus.RUNNING.value

    completed = client.post(
        f"/projects/{project_id}/media-generation-jobs/{job_id}/complete-mock",
        headers=auth_headers,
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == MediaGenerationJobStatus.SUCCEEDED.value
    assert body["media_asset_id"] is not None
    assert "b64" not in str(body["result_metadata"]).lower()

    brief = client.get(
        f"/projects/{project_id}/media-briefs/{brief_id}",
        headers=auth_headers,
    ).json()
    row = await MediaAssetRepository(db_session).get_by_id_for_owner(
        UUID(body["media_asset_id"]),
        UUID(brief["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.status == MediaAssetStatus.DRAFT
    assert row.generation_provider == "mock"
    assert row.source_generation_job_id == UUID(job_id)

    job_row = await MediaGenerationJobRepository(db_session).get_by_id_for_owner(
        UUID(job_id),
        UUID(brief["owner_id"]),
        UUID(project_id),
    )
    assert job_row is not None
    assert job_row.status == MediaGenerationJobStatus.SUCCEEDED


def test_content_asset_cannot_start_generation_directly(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/generation-jobs",
        json={"provider": "mock"},
        headers=auth_headers,
    )
    assert response.status_code == 404

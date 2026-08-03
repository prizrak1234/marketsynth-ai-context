"""Phase AI.58 — Media asset storage boundary (metadata/refs only)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.media_asset_versions import MediaAssetVersionRepository
from app.marketing.media_contracts import MediaAssetStatus
from app.media_generation.contracts import MediaGenerationJobStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief


def _approved_brief(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = approved_content_asset_id(client, headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, headers, project_id, brief_id)
    return brief_id


@pytest.mark.asyncio
async def test_generation_creates_version_and_provenance(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.58 Storage"},
        headers=auth_headers,
    ).json()["id"]
    brief_id = _approved_brief(client, auth_headers, project_id)

    job = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock"},
        headers=auth_headers,
    ).json()
    job_id = job["id"]
    completed = client.post(
        f"/projects/{project_id}/media-generation-jobs/{job_id}/complete-mock",
        headers=auth_headers,
    ).json()
    media_asset_id = completed["media_asset_id"]

    detail = client.get(
        f"/projects/{project_id}/media-assets/{media_asset_id}",
        headers=auth_headers,
    ).json()
    assert detail["source_generation_job_id"] == job_id
    assert detail["provider"] == "mock"
    assert detail["storage_uri"]
    assert detail["current_version_number"] == 1
    blob = str(detail)
    assert "base64" not in blob.lower()

    brief = client.get(
        f"/projects/{project_id}/media-briefs/{brief_id}",
        headers=auth_headers,
    ).json()
    versions = await MediaAssetVersionRepository(db_session).list_versions(
        UUID(media_asset_id),
        UUID(brief["owner_id"]),
        UUID(project_id),
    )
    assert len(versions) == 1
    assert versions[0].source_generation_job_id == UUID(job_id)
    assert versions[0].storage_uri == detail["storage_uri"]


def test_no_raw_payload_in_job_result_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.58 meta"}, headers=auth_headers).json()[
        "id"
    ]
    brief_id = _approved_brief(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock"},
        headers=auth_headers,
    ).json()["id"]
    completed = client.post(
        f"/projects/{project_id}/media-generation-jobs/{job_id}/complete-mock",
        headers=auth_headers,
    ).json()
    meta = completed["result_metadata"]
    assert "api_key" not in meta
    assert "raw_response" not in meta

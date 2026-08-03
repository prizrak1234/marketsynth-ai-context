"""Phase AI.55 — Media production layer freeze invariants (AI.50–AI.54)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.marketing.media_contracts import MediaAssetStatus, MediaBriefStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief

_FORBIDDEN_PROVIDER_MARKERS = (
    "flux",
    "dall-e",
    "dalle",
    "midjourney",
    "openai-images",
    "heygen",
    "canva",
    "fal.ai",
)


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.55 Freeze"}, headers=headers).json()["id"]


@pytest.mark.asyncio
async def test_full_media_production_chain_no_generation(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)

    brief_resp = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={"title": "Visual brief"},
        headers=auth_headers,
    )
    assert brief_resp.status_code == 201
    brief_id = brief_resp.json()["media_brief_id"]

    client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/approve",
        headers=auth_headers,
    )

    asset_resp = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )
    assert asset_resp.status_code == 201

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    owner_id = UUID(asset["owner_id"])
    project_uuid = UUID(project_id)

    brief_row = await MediaBriefRepository(db_session).get_by_id_for_owner(
        UUID(brief_id),
        owner_id,
        project_uuid,
    )
    assert brief_row is not None
    assert brief_row.status == MediaBriefStatus.APPROVED
    assert brief_row.submitted_for_review_at is not None
    assert brief_row.approved_at is not None

    media_row = await MediaAssetRepository(db_session).get_by_id_for_owner(
        UUID(asset_resp.json()["media_asset_id"]),
        owner_id,
        project_uuid,
    )
    assert media_row is not None
    assert media_row.status == MediaAssetStatus.DRAFT
    assert media_row.generation_provider == "placeholder"
    assert media_row.generation_metadata.get("placeholder") is True
    for marker in _FORBIDDEN_PROVIDER_MARKERS:
        assert marker not in (media_row.generation_provider or "").lower()


def test_no_generation_routes_on_media_layer(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    media_paths = [
        path
        for path in paths
        if "/media-briefs" in path or "/media-assets" in path or "create-media" in path
    ]
    assert media_paths
    forbidden_suffixes = ("/generate", "/render", "/publish", "/send")
    for path_key in media_paths:
        for suffix in forbidden_suffixes:
            assert suffix not in path_key
        blob = path_key.lower()
        for marker in _FORBIDDEN_PROVIDER_MARKERS:
            assert marker not in blob

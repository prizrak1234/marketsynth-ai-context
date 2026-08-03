"""Phase AI.54 — Approved MediaBrief → MediaAsset placeholder."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.media_assets import MediaAssetRepository
from app.marketing.media_contracts import MediaAssetStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.54 Conversion"}, headers=headers).json()["id"]


def test_draft_brief_cannot_create_media_asset(
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
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "approved" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_placeholder_from_approved_brief(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, auth_headers, project_id, brief_id)

    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["media_asset_status"] == MediaAssetStatus.DRAFT.value

    detail = client.get(
        f"/projects/{project_id}/media-assets/{body['media_asset_id']}",
        headers=auth_headers,
    ).json()
    assert detail["generation_provider"] == "placeholder"
    assert detail["generation_metadata"].get("placeholder") is True
    assert detail["source_media_brief_id"] == brief_id

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
    assert row.source_media_brief_id == UUID(brief_id)


def test_duplicate_media_type_rejected(
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
    approve_media_brief(client, auth_headers, project_id, brief_id)

    first = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_approve_brief_does_not_auto_create_media_asset(
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
    approve_media_brief(client, auth_headers, project_id, brief_id)

    listed = client.get(
        f"/projects/{project_id}/media-assets",
        params={"media_brief_id": brief_id},
        headers=auth_headers,
    ).json()
    assert listed == []

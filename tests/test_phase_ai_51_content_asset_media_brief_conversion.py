"""Phase AI.51 — Approved ContentAsset → MediaBrief draft (explicit)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.media_briefs import MediaBriefRepository
from app.marketing.media_contracts import MediaBriefStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "AI.51 Brief"},
        headers=headers,
    ).json()["id"]


def test_draft_asset_cannot_create_media_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Draft", "body": "x"},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "approved" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_media_brief_from_approved_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={"platform": "instagram", "goal": "Drive signups"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["media_brief_status"] == MediaBriefStatus.DRAFT.value

    detail = client.get(
        f"/projects/{project_id}/media-briefs/{body['media_brief_id']}",
        headers=auth_headers,
    ).json()
    assert detail["status"] == MediaBriefStatus.DRAFT.value
    assert detail["source_content_asset_id"] == asset_id
    assert detail["content_asset_id"] == asset_id
    assert detail["platform"] == "instagram"

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    row = await MediaBriefRepository(db_session).get_by_id_for_owner(
        UUID(body["media_brief_id"]),
        UUID(asset["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.source_content_asset_id == UUID(asset_id)


def test_duplicate_media_brief_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    first = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    )
    assert second.status_code == 409

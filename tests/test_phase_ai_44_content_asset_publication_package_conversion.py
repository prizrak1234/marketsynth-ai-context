"""Phase AI.44 — Approved ContentAsset → PublicationPackage draft (explicit)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "AI.44 Conversion"},
        headers=headers,
    ).json()["id"]


def _draft_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Pkg source", "body": "Body text"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_non_approved_asset_cannot_create_package(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _draft_asset(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "approved" in response.json()["detail"].lower()


def test_review_asset_cannot_create_package(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _draft_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_package_from_approved_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _draft_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "linkedin", "title": "Custom title"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["publication_package_status"] == PublicationPackageStatus.DRAFT.value

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    owner_id = UUID(asset["owner_id"])

    row = await PublicationPackageRepository(db_session).get_by_id_for_owner(
        UUID(body["publication_package_id"]),
        owner_id,
        UUID(project_id),
    )
    assert row is not None
    assert row.source_content_asset_id == UUID(asset_id)
    assert row.status == PublicationPackageStatus.DRAFT
    assert row.title == "Custom title"


def test_duplicate_channel_package_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _draft_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    first = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_approve_asset_does_not_auto_create_package(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _draft_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    listed = client.get(
        f"/projects/{project_id}/publication-packages",
        params={"content_asset_id": asset_id},
        headers=auth_headers,
    ).json()
    assert listed == []

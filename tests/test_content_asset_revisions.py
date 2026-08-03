"""Phase 4.5 — create draft revision from approved content asset."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.marketing import ContentAssetTable
from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.tools.errors import ToolValidationError
from app.tools.executors.content_asset_create_draft import (
    parse_content_asset_create_draft_arguments,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Revisions"},
        headers=headers,
    ).json()["id"]


def _create_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Original",
    body: str = "approved copy",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": title, "body": body},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _approve(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str) -> dict:
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


def _create_revision(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    source_id: str,
    *,
    payload: dict | None = None,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json=payload or {},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_approved_asset_can_create_draft_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(client, auth_headers, project_id, source_id)
    assert revision["status"] == "draft"
    assert revision["source_asset_id"] == source_id
    assert revision["source_version_number"] == 1
    assert revision["revision_number"] == 1


def test_draft_source_cannot_create_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    draft_id = _create_draft(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{draft_id}/create-revision",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_source_cannot_create_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)
    client.post(
        f"/projects/{project_id}/content-assets/{source_id}/archive",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_approved_without_approved_version_number_rejected(
    db_session: AsyncSession,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    approved = _approve(client, auth_headers, project_id, source_id)

    row = await db_session.get(ContentAssetTable, UUID(approved["id"]))
    assert row is not None
    row.approved_version_number = None
    db_session.add(row)
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_revision_copies_approved_version_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(
        client,
        auth_headers,
        project_id,
        title="Approved title",
        body="Approved body",
    )
    client.patch(
        f"/projects/{project_id}/content-assets/{source_id}",
        json={"body": "Draft tweak before approve"},
        headers=auth_headers,
    )
    _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(client, auth_headers, project_id, source_id)
    assert revision["title"] == "Approved title"
    assert revision["body"] == "Draft tweak before approve"


def test_revision_can_override_title_and_body(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(
        client,
        auth_headers,
        project_id,
        source_id,
        payload={"title": "Revision title", "body": "Revision body"},
    )
    assert revision["title"] == "Revision title"
    assert revision["body"] == "Revision body"


def test_revision_links_source_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    approved = _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(client, auth_headers, project_id, source_id)
    assert revision["source_asset_id"] == source_id
    assert revision["source_version_number"] == approved["approved_version_number"]


def test_revision_number_increments_per_source(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    first = _create_revision(client, auth_headers, project_id, source_id)
    second = _create_revision(client, auth_headers, project_id, source_id)
    assert first["revision_number"] == 1
    assert second["revision_number"] == 2


def test_source_asset_not_mutated(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id, body="immutable")
    approved = _approve(client, auth_headers, project_id, source_id)
    _create_revision(
        client,
        auth_headers,
        project_id,
        source_id,
        payload={"body": "revision body"},
    )

    source = client.get(
        f"/projects/{project_id}/content-assets/{source_id}",
        headers=auth_headers,
    ).json()
    assert source["body"] == approved["body"]
    assert source["status"] == "approved"


def test_new_revision_is_draft_with_version_1(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(client, auth_headers, project_id, source_id)
    assert revision["status"] == "draft"
    assert revision["current_version_number"] == 1
    assert revision["approved_version_number"] is None

    versions = client.get(
        f"/projects/{project_id}/content-assets/{revision['id']}/versions",
        headers=auth_headers,
    ).json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1


def test_revision_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json={},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_get_asset_includes_revision_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)
    revision = _create_revision(client, auth_headers, project_id, source_id)

    fetched = client.get(
        f"/projects/{project_id}/content-assets/{revision['id']}",
        headers=auth_headers,
    ).json()
    assert fetched["source_asset_id"] == source_id
    assert fetched["revision_number"] == 1


def test_list_assets_includes_revision_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)
    _create_revision(client, auth_headers, project_id, source_id)

    items = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    revision_rows = [item for item in items if item.get("source_asset_id") == source_id]
    assert len(revision_rows) == 1
    assert revision_rows[0]["revision_number"] == 1


def test_create_draft_rejects_revision_fields() -> None:
    with pytest.raises(ToolValidationError, match="source_asset_id"):
        parse_content_asset_create_draft_arguments(
            {
                "type": "email",
                "title": "T",
                "body": "B",
                "source_asset_id": "00000000-0000-0000-0000-000000000001",
            },
        )


def test_revision_can_be_approved_via_existing_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)
    revision = _create_revision(client, auth_headers, project_id, source_id)

    approved_revision = client.post(
        f"/projects/{project_id}/content-assets/{revision['id']}/approve",
        headers=auth_headers,
    ).json()
    assert approved_revision["status"] == "approved"
    assert approved_revision["approved_version_number"] == 1


@pytest.mark.asyncio
async def test_revision_metadata_includes_revision_block(
    db_session: AsyncSession,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(
        client,
        auth_headers,
        project_id,
        body="body",
    )
    client.patch(
        f"/projects/{project_id}/content-assets/{source_id}",
        json={"metadata": {"tone": "formal"}},
        headers=auth_headers,
    )
    _approve(client, auth_headers, project_id, source_id)

    revision = _create_revision(
        client,
        auth_headers,
        project_id,
        source_id,
        payload={"metadata": {"channel": "email"}},
    )
    assert revision["metadata"]["tone"] == "formal"
    assert revision["metadata"]["channel"] == "email"
    assert revision["metadata"]["revision"]["source_asset_id"] == source_id

    versions_repo = ContentAssetVersionRepository(db_session)
    versions = await versions_repo.list_versions(
        UUID(revision["id"]),
        UUID(revision["owner_id"]),
        UUID(revision["project_id"]),
    )
    assert len(versions) == 1

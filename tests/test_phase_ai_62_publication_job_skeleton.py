"""Phase AI.62 — Publication package job skeleton."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


def test_draft_package_cannot_create_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from tests.publishing_workflow import _approved_asset_id

    project_id = client.post("/projects", json={"name": "AI.62"}, headers=auth_headers).json()[
        "id"
    ]
    asset_id = _approved_asset_id(client, auth_headers, project_id)
    package_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    ).json()["publication_package_id"]
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_job_snapshots_package_immutable(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.db.repositories.publication_packages import PublicationPackageRepository

    project_id = client.post("/projects", json={"name": "AI.62 snap"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert created.status_code == 201
    job = created.json()
    assert job["status"] == PublicationPackageJobStatus.QUEUED.value
    snapshot_title = job["payload_snapshot"]["title"]

    pkg_repo = PublicationPackageRepository(db_session)
    pkg_row = await pkg_repo.get_by_id_for_owner(
        UUID(package_id),
        UUID(job["owner_id"]),
        UUID(project_id),
    )
    assert pkg_row is not None
    pkg_row.title = "Changed after job"
    await pkg_repo.update(pkg_row)

    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(job["id"]),
        UUID(job["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.payload_snapshot["title"] == snapshot_title


@pytest.mark.asyncio
async def test_duplicate_active_job_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.62 dup"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    first = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert second.status_code == 409

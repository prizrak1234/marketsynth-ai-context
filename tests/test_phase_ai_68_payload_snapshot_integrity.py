"""Phase AI.68 — Payload snapshot immutability audit."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.publishing_foundation.snapshot_hash import compute_snapshot_hash
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


@pytest.mark.asyncio
async def test_package_edit_does_not_change_snapshot_hash(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.db.repositories.publication_packages import PublicationPackageRepository

    project_id = client.post("/projects", json={"name": "AI.68"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()
    original_hash = created["snapshot_hash"]
    assert original_hash is not None

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    pkg = await PublicationPackageRepository(db_session).get_by_id_for_owner(
        UUID(package_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert pkg is not None
    pkg.title = "Tampered package title only"
    await PublicationPackageRepository(db_session).update(pkg)

    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(created["id"]),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.snapshot_hash == original_hash
    assert compute_snapshot_hash(dict(row.payload_snapshot or {})) == original_hash


@pytest.mark.asyncio
async def test_tampered_snapshot_fails_on_start(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.68 tamper"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()

    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(created["id"]),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    tampered = dict(row.payload_snapshot or {})
    tampered["title"] = "Injected title in DB"
    row.payload_snapshot = tampered
    await PublicationPackageJobRepository(db_session).update(row)

    started = client.post(
        f"/projects/{project_id}/publication-package-jobs/{created['id']}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    assert started.json()["status"] == PublicationPackageJobStatus.FAILED.value
    assert started.json()["error"]["error_code"] == "snapshot_tampered"


@pytest.mark.asyncio
async def test_tampered_snapshot_fails_on_execute_dry_run(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.68 exec"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()

    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(created["id"]),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    tampered = dict(row.payload_snapshot or {})
    tampered["body"] = "tampered body"
    row.payload_snapshot = tampered
    await PublicationPackageJobRepository(db_session).update(row)

    executed = client.post(
        f"/projects/{project_id}/publication-package-jobs/{created['id']}/execute-dry-run",
        headers=auth_headers,
    )
    assert executed.status_code == 200
    assert executed.json()["error"]["error_code"] == "snapshot_tampered"

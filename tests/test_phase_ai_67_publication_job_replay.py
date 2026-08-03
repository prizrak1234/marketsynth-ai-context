"""Phase AI.67 — Publication job replay."""

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


async def _failed_job_id(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> tuple[str, str, str, dict]:
    project_id = client.post("/projects", json={"name": "AI.67"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(job["id"]),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.status = PublicationPackageJobStatus.FAILED
    row.finished_at = row.created_at
    await PublicationPackageJobRepository(db_session).update(row)
    snapshot = dict(row.payload_snapshot or {})
    return project_id, job["id"], project["owner_id"], snapshot


@pytest.mark.asyncio
async def test_replay_failed_job_preserves_snapshot(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, failed_id, _owner_id, snapshot = await _failed_job_id(
        client,
        auth_headers,
        db_session,
    )
    replay = client.post(
        f"/projects/{project_id}/publication-package-jobs/{failed_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 201
    body = replay.json()
    assert body["status"] == PublicationPackageJobStatus.QUEUED.value
    assert body["replay_of_job_id"] == failed_id
    assert body["payload_snapshot"] == snapshot


@pytest.mark.asyncio
async def test_replay_cancelled_allowed(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, job_id, owner_id, _ = await _failed_job_id(
        client,
        auth_headers,
        db_session,
    )
    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(job_id),
        UUID(owner_id),
        UUID(project_id),
    )
    assert row is not None
    row.status = PublicationPackageJobStatus.CANCELLED
    await PublicationPackageJobRepository(db_session).update(row)

    replay = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 201


def test_replay_blocked_for_succeeded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.67 block"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute-dry-run",
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_replay_blocked_for_queued(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.67 queued"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409

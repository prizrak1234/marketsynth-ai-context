"""Phase AI.69 — Publishing reliability freeze invariants."""

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


def test_reliability_stack_idempotency_replay_dry_run_only(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.69"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    headers = {**auth_headers, "Idempotency-Key": "freeze-key"}

    job = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    ).json()
    dup = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    assert dup.json()["id"] == job["id"]

    completed = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job['id']}/execute-dry-run",
        headers=auth_headers,
    ).json()
    assert completed["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value
    assert completed["result_metadata"].get("dry_run") is True

    replay_blocked = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job['id']}/replay",
        headers=auth_headers,
    )
    assert replay_blocked.status_code == 409


@pytest.mark.asyncio
async def test_snapshot_hash_present_on_create(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.69 hash"},
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
    assert row.snapshot_hash is not None
    assert len(row.snapshot_hash) == 64


def test_no_scheduler_endpoints_in_openapi(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    for path_key in spec.get("paths", {}):
        assert "schedule" not in path_key.lower() or "publication-package" not in path_key

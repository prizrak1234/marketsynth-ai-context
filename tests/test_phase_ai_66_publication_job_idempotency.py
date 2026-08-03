"""Phase AI.66 — Publication job idempotency."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


def test_idempotent_create_returns_same_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.66"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    headers = {**auth_headers, "Idempotency-Key": "create-job-v1"}

    first = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_idempotency_fingerprint_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.66 conflict"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_a = active_foundation_channel_id(client, auth_headers, project_id)
    channel_b = active_foundation_channel_id(
        client,
        auth_headers,
        project_id,
        channel_type="instagram",
    )
    headers = {**auth_headers, "Idempotency-Key": "shared-key"}

    first = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_a},
        headers=headers,
    )
    assert first.status_code == 201

    conflict = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_b},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert "idempotency_fingerprint_conflict" in conflict.json()["detail"]


@pytest.mark.asyncio
async def test_no_raw_idempotency_key_in_db(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.66 hash"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    raw_key = "my-secret-idempotency-key-xyz"
    created = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers={**auth_headers, "Idempotency-Key": raw_key},
    )
    job_id = created.json()["id"]
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()

    row = await PublicationPackageJobRepository(db_session).get_by_id_for_owner(
        UUID(job_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    assert row.idempotency_key_hash is not None
    assert row.idempotency_fingerprint is not None
    assert raw_key not in str(row.idempotency_key_hash)
    row_dict = row.model_dump()
    assert raw_key not in str(row_dict)

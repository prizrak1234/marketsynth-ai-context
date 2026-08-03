"""Phase AI.65 — Publishing foundation freeze invariants."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)

_FORBIDDEN_OPENAPI = ("heygen", "canva", "instagram.com/api")


def test_openapi_has_no_real_publish_paths(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    for path_key in paths:
        lowered = path_key.lower()
        assert "/send-to-telegram" not in lowered
        assert "/instagram/publish" not in lowered
        for method, operation in paths[path_key].items():
            if method.startswith("x-"):
                continue
            blob = f"{operation.get('operationId', '')} {operation.get('summary', '')}".lower()
            for marker in _FORBIDDEN_OPENAPI:
                assert marker not in blob


def test_only_approved_package_and_active_channel(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.65"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()
    completed = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job['id']}/execute-dry-run",
        headers=auth_headers,
    ).json()
    assert completed["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value
    assert completed["result_metadata"].get("dry_run") is True


@pytest.mark.asyncio
async def test_legacy_publication_jobs_table_untouched_count(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Package jobs live in publication_package_jobs, not legacy asset queue."""
    from app.db.models.publishing import PublicationJobTable

    project_id = client.post("/projects", json={"name": "AI.65 legacy"}, headers=auth_headers).json()[
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

    legacy_count = (
        await db_session.execute(
            select(func.count()).select_from(PublicationJobTable).where(
                PublicationJobTable.project_id == UUID(project_id),
            ),
        )
    ).scalar_one()
    assert legacy_count == 0

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    package_jobs = await PublicationPackageJobRepository(db_session).list_by_project(
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert len(package_jobs) == 1
    assert isinstance(package_jobs[0], PublicationPackageJobTable)

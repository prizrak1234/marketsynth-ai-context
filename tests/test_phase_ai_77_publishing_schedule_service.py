"""Phase AI.77 — Publishing schedule due scanner and explicit dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import queued_publication_package_job_id


@pytest.mark.asyncio
async def test_due_scanner_returns_only_due_queued_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post("/projects", json={"name": "AI.77"}, headers=auth_headers).json()[
        "id"
    ]
    due_job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    future_job_id = queued_publication_package_job_id(client, auth_headers, project_id)

    when_future = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{future_job_id}/schedule",
        json={"scheduled_for": when_future},
        headers=auth_headers,
    )

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    repo = PublicationPackageJobRepository(db_session)
    due_row = await repo.get_by_id_for_owner(
        UUID(due_job_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert due_row is not None
    due_row.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    due_row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
    await repo.update(due_row)

    due_list = client.get(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/due",
        headers=auth_headers,
    ).json()
    due_ids = {item["id"] for item in due_list}
    assert due_job_id in due_ids
    assert future_job_id not in due_ids
    for item in due_list:
        assert item["status"] == PublicationPackageJobStatus.QUEUED.value


def test_dispatch_due_not_yet_due_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.77 not due"},
        headers=auth_headers,
    ).json()["id"]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    when = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/{job_id}/dispatch-due",
        json={"mode": "dry_run"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_explicit_dispatch_dry_run(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.77 dispatch"},
        headers=auth_headers,
    ).json()["id"]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    repo = PublicationPackageJobRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(job_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.scheduled_for = datetime.now(UTC) - timedelta(seconds=30)
    row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
    await repo.update(row)

    response = client.post(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/{job_id}/dispatch-due",
        json={"mode": "dry_run"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value
    assert body["schedule_status"] == PublicationPackageJobScheduleStatus.DISPATCHED.value
    assert body["dispatch_attempts"] >= 1

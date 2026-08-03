"""Phase AI.79 — Publishing scheduler freeze invariants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.publishing_foundation.contracts import PublicationPackageJobScheduleStatus
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
    queued_publication_package_job_id,
)


def test_openapi_has_scheduler_paths_no_background_worker_route(
    client: TestClient,
) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    assert any("scheduled-jobs/due" in key for key in paths)
    assert any("/schedule" in key for key in paths)
    assert not any("scheduler-loop" in key.lower() for key in paths)


@pytest.mark.asyncio
async def test_instagram_real_dispatch_blocked(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_PUBLISHING_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    project_id = client.post(
        "/projects",
        json={"name": "AI.79 ig"},
        headers=auth_headers,
    ).json()["id"]
    package_id = approved_publication_package_id(
        client,
        auth_headers,
        project_id,
        channel="instagram",
    )
    channel_id = active_foundation_channel_id(
        client,
        auth_headers,
        project_id,
        channel_type="instagram",
    )
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    repo = PublicationPackageJobRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(job_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
    await repo.update(row)

    response = client.post(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/{job_id}/dispatch-due",
        json={"mode": "real"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "not enabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_no_auto_worker_module_for_package_scheduler(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Due jobs are listed only via explicit GET; no implicit dispatch on list."""
    project_id = client.post(
        "/projects",
        json={"name": "AI.79 explicit"},
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
    row.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
    await repo.update(row)

    listed = client.get(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/due",
        headers=auth_headers,
    ).json()
    assert any(item["id"] == job_id for item in listed)

    refreshed = await repo.get_by_id_for_owner(
        UUID(job_id),
        UUID(project["owner_id"]),
        UUID(project_id),
    )
    assert refreshed is not None
    assert refreshed.status.value == "queued"
    assert refreshed.schedule_status == PublicationPackageJobScheduleStatus.SCHEDULED

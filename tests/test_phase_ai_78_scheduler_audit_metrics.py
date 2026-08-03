"""Phase AI.78 — Scheduler audit events and metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publishing_audit_events import PublishingAuditEventRepository
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublishingAuditEventType,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import queued_publication_package_job_id


@pytest.mark.asyncio
async def test_scheduler_audit_and_metrics(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post("/projects", json={"name": "AI.78"}, headers=auth_headers).json()[
        "id"
    ]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    when = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )

    metrics = client.get(
        f"/projects/{project_id}/publishing-foundation/metrics",
        headers=auth_headers,
    ).json()
    assert metrics["scheduled_jobs_total"] >= 1
    assert metrics["scheduled_jobs_by_channel_type"].get("telegram", 0) >= 1

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    owner_id = UUID(project["owner_id"])
    repo = PublicationPackageJobRepository(db_session)
    row = await repo.get_by_id_for_owner(UUID(job_id), owner_id, UUID(project_id))
    assert row is not None
    row.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
    await repo.update(row)

    client.post(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/{job_id}/dispatch-due",
        json={"mode": "dry_run"},
        headers=auth_headers,
    )

    metrics_after = client.get(
        f"/projects/{project_id}/publishing-foundation/metrics",
        headers=auth_headers,
    ).json()
    assert metrics_after["dispatched_jobs_total"] >= 1

    events = await PublishingAuditEventRepository(db_session).list_by_project(
        owner_id,
        UUID(project_id),
        limit=100,
    )
    event_types = {e.event_type for e in events}
    assert PublishingAuditEventType.JOB_SCHEDULED in event_types
    assert PublishingAuditEventType.JOB_DISPATCH_REQUESTED in event_types
    assert PublishingAuditEventType.JOB_DISPATCHED in event_types

    for event in events:
        blob = str(event.safe_metadata)
        assert "bot_token" not in blob
        assert "payload_snapshot" not in event.safe_metadata

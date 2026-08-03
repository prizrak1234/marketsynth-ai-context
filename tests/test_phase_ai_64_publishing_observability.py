"""Phase AI.64 — Publishing foundation observability."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.publishing_audit_events import PublishingAuditEventRepository
from app.publishing_foundation.contracts import PublishingAuditEventType
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


@pytest.mark.asyncio
async def test_metrics_and_audit_after_dry_run(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post("/projects", json={"name": "AI.64"}, headers=auth_headers).json()[
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

    metrics = client.get(
        f"/projects/{project_id}/publishing-foundation/metrics",
        headers=auth_headers,
    ).json()
    assert metrics["jobs_total"] >= 1
    assert metrics["jobs_by_status"].get("dry_run_succeeded", 0) >= 1
    assert metrics["jobs_by_channel_type"].get("telegram", 0) >= 1
    assert metrics["latest_activity_at"] is not None

    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    owner_id = UUID(project["owner_id"])
    events = await PublishingAuditEventRepository(db_session).list_by_project(
        owner_id,
        UUID(project_id),
        limit=50,
    )
    event_types = {e.event_type for e in events}
    assert PublishingAuditEventType.JOB_CREATED in event_types
    assert PublishingAuditEventType.JOB_DRY_RUN_SUCCEEDED in event_types

    for event in events:
        assert "bot_token" not in str(event.safe_metadata)
        assert "payload_snapshot" not in event.safe_metadata

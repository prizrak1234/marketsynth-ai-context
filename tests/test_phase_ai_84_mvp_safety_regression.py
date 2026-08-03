"""Phase AI.84 — MVP safety regression across frozen layers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublishingChannelTable
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.marketing.contracts import PublicationPackageStatus
from app.publishing_foundation.contracts import PublicationPackageJobScheduleStatus
from app.schemas.contracts import ChatBlockActionType, MarketingSpecialistType
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.media_workflow import approved_content_asset_id, approve_media_brief
from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
    queued_publication_package_job_id,
)

_FORBIDDEN_METADATA_MARKERS = (
    "bot_token",
    "api_key",
    "secret",
    "password",
    "BEGIN PRIVATE KEY",
)
_BASE64_BLOB_MARKERS = ("data:image/", ";base64,")


def _approved_plan_and_run(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> tuple[str, str]:
    orchestrator = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator"},
        headers=headers,
    ).json()["id"]
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Сделай контент-стратегию", "agent_id": orchestrator},
        headers=headers,
    ).json()
    plan_id = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=headers,
    ).json()["created_resource_id"]
    client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=headers,
    )
    run_id = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    ).json()["id"]
    return plan_id, run_id


@pytest.mark.asyncio
async def test_no_secrets_in_channel_and_job_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post("/projects", json={"name": "AI.84 secrets"}, headers=auth_headers).json()[
        "id"
    ]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)

    channels = (
        await db_session.execute(
            select(PublishingChannelTable).where(
                PublishingChannelTable.project_id == UUID(project_id),
            ),
        )
    ).scalars().all()
    jobs = (
        await db_session.execute(
            select(PublicationPackageJobTable).where(
                PublicationPackageJobTable.id == UUID(job_id),
            ),
        )
    ).scalar_one()

    for channel in channels:
        blob = str(channel.config or {}).lower()
        for marker in _FORBIDDEN_METADATA_MARKERS:
            assert marker not in blob
    for field in (jobs.payload_snapshot, jobs.result_metadata, jobs.error, jobs.last_dispatch_error):
        if field:
            blob = str(field).lower()
            for marker in _FORBIDDEN_METADATA_MARKERS:
                assert marker not in blob


@pytest.mark.asyncio
async def test_no_base64_blobs_in_media_asset_storage(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.db.models.media import MediaAssetTable

    project_id = client.post("/projects", json={"name": "AI.84 b64"}, headers=auth_headers).json()[
        "id"
    ]
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, auth_headers, project_id, brief_id)
    client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/create-media-asset",
        json={"media_type": "image"},
        headers=auth_headers,
    )

    rows = (
        await db_session.execute(
            select(MediaAssetTable).where(MediaAssetTable.project_id == UUID(project_id)),
        )
    ).scalars().all()
    for row in rows:
        blob = str(row.storage_metadata or "") + str(row.preview_metadata or "")
        for marker in _BASE64_BLOB_MARKERS:
            assert marker not in blob


def test_no_publish_from_unapproved_package(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.84 pkg"}, headers=auth_headers).json()[
        "id"
    ]
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    package_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    ).json()["publication_package_id"]
    client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/submit-review",
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_no_media_generation_from_unapproved_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.84 brief"}, headers=auth_headers).json()[
        "id"
    ]
    asset_id = approved_content_asset_id(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=auth_headers,
    ).json()["media_brief_id"]
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "mock", "media_type": "image"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_no_content_asset_from_unapproved_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.84 cw"}, headers=auth_headers).json()[
        "id"
    ]
    _plan_id, run_id = _approved_plan_and_run(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/start",
        headers=auth_headers,
    )
    run = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}",
        headers=auth_headers,
    ).json()
    idx = next(
        i
        for i, t in enumerate(run["task_snapshots"])
        if t["specialist"] == MarketingSpecialistType.COPYWRITER.value
    )
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/tasks/{idx}/execute-specialist",
        headers=auth_headers,
    )
    outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run_id, "specialist": "copywriter"},
        headers=auth_headers,
    ).json()
    response = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{outputs[0]['id']}/create-content-asset",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_no_execution_run_from_draft_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.84 draft"}, headers=auth_headers).json()[
        "id"
    ]
    orchestrator = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator"},
        headers=auth_headers,
    ).json()["id"]
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "План без апрува", "agent_id": orchestrator},
        headers=auth_headers,
    ).json()
    draft_plan_id = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=auth_headers,
    ).json()["created_resource_id"]
    response = client.post(
        f"/projects/{project_id}/marketing-plans/{draft_plan_id}/execution-runs",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_no_scheduler_background_worker_route(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = " ".join(spec.get("paths", {}).keys()).lower()
    assert "scheduler-loop" not in paths
    assert "background" not in paths or "scheduled-jobs/due" in paths


def test_dry_run_dispatch_without_telegram_env(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_PUBLISHING_ENABLED", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.84 dry"}, headers=auth_headers).json()[
        "id"
    ]
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
    await db_session.commit()

    response = client.post(
        f"/projects/{project_id}/publishing-foundation/scheduled-jobs/{job_id}/dispatch-due",
        json={"mode": "dry_run"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "dry_run_succeeded"
    get_settings.cache_clear()


def test_telegram_real_dispatch_feature_gated(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_PUBLISHING_ENABLED", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.84 real"}, headers=auth_headers).json()[
        "id"
    ]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute",
        headers=auth_headers,
    )
    assert response.status_code == 409
    get_settings.cache_clear()

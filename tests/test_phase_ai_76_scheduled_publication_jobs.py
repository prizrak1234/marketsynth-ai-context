"""Phase AI.76 — Scheduled publication package jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from fastapi.testclient import TestClient

from tests.publishing_workflow import queued_publication_package_job_id


def test_schedule_queued_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.76"}, headers=auth_headers).json()[
        "id"
    ]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    when = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schedule_status"] == "scheduled"
    assert body["scheduled_for"] is not None


def test_past_schedule_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.76 past"},
        headers=auth_headers,
    ).json()["id"]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    when = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_terminal_job_cannot_be_scheduled(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.76 terminal"},
        headers=auth_headers,
    ).json()["id"]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute-dry-run",
        headers=auth_headers,
    )
    when = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_unschedule_scheduled_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "AI.76 unsched"},
        headers=auth_headers,
    ).json()["id"]
    job_id = queued_publication_package_job_id(client, auth_headers, project_id)
    when = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/schedule",
        json={"scheduled_for": when},
        headers=auth_headers,
    )
    response = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/unschedule",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["schedule_status"] == "unscheduled"
    assert response.json()["scheduled_for"] is None

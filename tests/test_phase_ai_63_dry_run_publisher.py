"""Phase AI.63 — Dry-run publisher (no HTTP)."""

from __future__ import annotations

from app.publishing_foundation.contracts import PublicationPackageJobStatus
from fastapi.testclient import TestClient

from tests.publishing_workflow import (
    active_foundation_channel_id,
    approved_publication_package_id,
)


def test_dry_run_job_lifecycle(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.63"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    started = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/start",
        headers=auth_headers,
    )
    assert started.status_code == 200
    assert started.json()["status"] == PublicationPackageJobStatus.RUNNING.value

    completed = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/complete-dry-run",
        headers=auth_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value
    assert completed.json()["result_metadata"].get("dry_run") is True
    assert "bot_token" not in str(completed.json())


def test_execute_dry_run_one_step(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.63 exec"}, headers=auth_headers).json()[
        "id"
    ]
    package_id = approved_publication_package_id(client, auth_headers, project_id)
    channel_id = active_foundation_channel_id(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    executed = client.post(
        f"/projects/{project_id}/publication-package-jobs/{job_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert executed.status_code == 200
    assert executed.json()["status"] == PublicationPackageJobStatus.DRY_RUN_SUCCEEDED.value

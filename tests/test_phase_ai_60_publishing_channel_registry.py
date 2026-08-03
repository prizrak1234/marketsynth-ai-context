"""Phase AI.60 — Publishing foundation channel registry."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.60"}, headers=headers).json()["id"]


def test_create_list_get_patch_archive_channel(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    created = client.post(
        f"/projects/{project_id}/publishing-foundation/channels",
        json={
            "name": "TG Foundation",
            "channel_type": "telegram",
            "status": "draft",
            "config_metadata": {"chat_id": "-1009990001"},
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    channel_id = created.json()["id"]
    assert created.json()["status"] == "draft"
    assert created.json()["config_metadata"]["chat_id"] == "-1009990001"

    listed = client.get(
        f"/projects/{project_id}/publishing-foundation/channels",
        headers=auth_headers,
    ).json()
    assert len(listed) == 1

    patched = client.patch(
        f"/projects/{project_id}/publishing-foundation/channels/{channel_id}",
        json={"status": "active"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "active"

    archived = client.post(
        f"/projects/{project_id}/publishing-foundation/channels/{channel_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    without_archived = client.get(
        f"/projects/{project_id}/publishing-foundation/channels",
        headers=auth_headers,
    ).json()
    assert without_archived == []


def test_config_rejects_secrets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/publishing-foundation/channels",
        json={
            "name": "Bad",
            "channel_type": "instagram",
            "config_metadata": {"bot_token": "secret-value"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_paused_channel_not_usable_for_jobs_later(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from tests.publishing_workflow import approved_publication_package_id

    project_id = _project_id(client, auth_headers)
    created = client.post(
        f"/projects/{project_id}/publishing-foundation/channels",
        json={
            "name": "Paused",
            "channel_type": "linkedin",
            "status": "paused",
        },
        headers=auth_headers,
    )
    channel_id = created.json()["id"]
    package_id = approved_publication_package_id(client, auth_headers, project_id, channel="linkedin")
    job_resp = client.post(
        f"/projects/{project_id}/publication-packages/{package_id}/publication-jobs",
        params={"channel_id": channel_id},
        headers=auth_headers,
    )
    assert job_resp.status_code == 409

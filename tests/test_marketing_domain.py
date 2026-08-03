"""Phase 4.0 — marketing domain CRUD and ownership."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Marketing domain"},
        headers=headers,
    ).json()["id"]


def test_create_marketing_brief(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={
            "title": "Q2 Launch",
            "product_description": "SaaS analytics",
            "target_audience": "B2B founders",
            "offer": "14-day trial",
            "goals": ["leads", "signups"],
            "constraints": {"tone": "professional"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Q2 Launch"
    assert body["status"] == "draft"
    assert body["project_id"] == project_id
    assert body["goals"] == ["leads", "signups"]


def test_list_briefs_by_project(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief A"},
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief B"},
        headers=auth_headers,
    )
    listed = client.get(
        f"/projects/{project_id}/marketing-briefs",
        headers=auth_headers,
    ).json()
    assert len(listed) == 2
    titles = {row["title"] for row in listed}
    assert titles == {"Brief A", "Brief B"}


def test_brief_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Owned brief"},
        headers=auth_headers,
    ).json()["id"]

    assert (
        client.get(
            f"/projects/{project_id}/marketing-briefs/{brief_id}",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/projects/{project_id}/marketing-briefs",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/projects/{project_id}/marketing-briefs/{brief_id}",
            json={"title": "Hijacked"},
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/projects/{project_id}/marketing-briefs/{brief_id}",
            headers=other_auth_headers,
        ).status_code
        == 404
    )


def test_update_brief_fields(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Original"},
        headers=auth_headers,
    ).json()["id"]

    updated = client.patch(
        f"/projects/{project_id}/marketing-briefs/{brief_id}",
        json={
            "title": "Updated title",
            "offer": "New offer",
            "status": "active",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["title"] == "Updated title"
    assert body["offer"] == "New offer"
    assert body["status"] == "active"


def test_archive_brief(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "To archive"},
        headers=auth_headers,
    ).json()["id"]

    archived = client.delete(
        f"/projects/{project_id}/marketing-briefs/{brief_id}",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    default_list = client.get(
        f"/projects/{project_id}/marketing-briefs",
        headers=auth_headers,
    ).json()
    assert all(row["id"] != brief_id for row in default_list)

    with_archived = client.get(
        f"/projects/{project_id}/marketing-briefs",
        headers=auth_headers,
        params={"include_archived": True},
    ).json()
    assert any(row["id"] == brief_id and row["status"] == "archived" for row in with_archived)


def test_create_content_asset(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": "Launch post",
            "body": "Hello founders",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "telegram_post"
    assert body["status"] == "draft"


def test_list_content_assets_by_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Email 1", "body": "a"},
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "ad_copy", "title": "Ad 1", "body": "b"},
        headers=auth_headers,
    )
    listed = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    assert len(listed) == 2


def test_list_content_assets_by_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Parent brief"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "landing_page",
            "title": "LP",
            "body": "copy",
            "brief_id": brief_id,
        },
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Unlinked", "body": "x"},
        headers=auth_headers,
    )

    by_brief = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
        params={"brief_id": brief_id},
    ).json()
    assert len(by_brief) == 1
    assert by_brief[0]["brief_id"] == brief_id


def test_content_asset_links_task_and_agent_run(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()

    project_id = _project_id(client, auth_headers)
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "Mkt"},
        headers=auth_headers,
    ).json()["id"]
    task_id = client.post(
        "/tasks",
        json={"project_id": project_id, "title": "Write copy"},
        headers=auth_headers,
    ).json()["id"]
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "draft"}},
        headers=auth_headers,
    ).json()["id"]

    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "article",
            "title": "Linked asset",
            "body": "body",
            "task_id": task_id,
            "agent_run_id": run_id,
        },
        headers=auth_headers,
    )
    assert asset.status_code == 201
    body = asset.json()
    assert body["task_id"] == task_id
    assert body["agent_run_id"] == run_id


def test_update_content_asset_body_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "offer", "title": "Offer v1", "body": "old"},
        headers=auth_headers,
    ).json()["id"]

    updated = client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "new copy", "status": "approved"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["body"] == "new copy"
    assert body["status"] == "approved"


def test_archive_content_asset(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "funnel_step", "title": "Step 1", "body": "x"},
        headers=auth_headers,
    ).json()["id"]

    archived = client.delete(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_asset_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Secret asset", "body": "x"},
        headers=auth_headers,
    ).json()["id"]

    assert (
        client.get(
            f"/projects/{project_id}/content-assets/{asset_id}",
            headers=other_auth_headers,
        ).status_code
        == 404
    )


def test_archived_assets_hidden_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "ad_copy", "title": "Ad", "body": "x"},
        headers=auth_headers,
    ).json()["id"]
    client.delete(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    )

    default_list = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    assert all(row["id"] != asset_id for row in default_list)

    with_archived = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
        params={"include_archived": True},
    ).json()
    assert any(row["id"] == asset_id and row["status"] == "archived" for row in with_archived)


def test_no_secrets_in_marketing_api_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    created = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "Safe",
            "body": "content",
            "metadata": {"note": "no api_key here"},
        },
        headers=auth_headers,
    ).json()
    serialized = str(created).lower()
    assert "sk-" not in serialized
    assert "bwhsec" not in serialized
    assert "signing_secret" not in serialized

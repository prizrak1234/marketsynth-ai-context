"""Phase 4.7 — rollback by creating draft revision from version."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.schemas.contracts import EventType
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Rollback"},
        headers=headers,
    ).json()["id"]


def _create_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Title",
    body: str = "Body",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": title, "body": body},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _approve(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def _rollback(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    source_id: str,
    *,
    version_number: int,
    reason: str | None = None,
) -> dict:
    payload: dict = {"version_number": version_number}
    if reason is not None:
        payload["reason"] = reason
    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_approved_asset_can_rollback_to_version_1(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id, body="version one")
    client.patch(
        f"/projects/{project_id}/content-assets/{source_id}",
        json={"body": "version two"},
        headers=auth_headers,
    )
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(
        client,
        auth_headers,
        project_id,
        source_id,
        version_number=1,
    )
    assert rollback["status"] == "draft"
    assert rollback["body"] == "version one"
    assert rollback["source_version_number"] == 1


def test_rollback_to_latest_version_creates_new_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id, body="v1")
    client.patch(
        f"/projects/{project_id}/content-assets/{source_id}",
        json={"body": "v2"},
        headers=auth_headers,
    )
    approved = _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(
        client,
        auth_headers,
        project_id,
        source_id,
        version_number=approved["current_version_number"],
    )
    assert rollback["status"] == "draft"
    assert rollback["body"] == "v2"


def test_source_asset_not_mutated(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id, body="stable")
    approved = _approve(client, auth_headers, project_id, source_id)
    _rollback(client, auth_headers, project_id, source_id, version_number=1)

    source = client.get(
        f"/projects/{project_id}/content-assets/{source_id}",
        headers=auth_headers,
    ).json()
    assert source["body"] == approved["body"]
    assert source["status"] == "approved"


def test_rollback_links_source_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    assert rollback["source_asset_id"] == source_id
    assert rollback["revision_number"] == 1


def test_revision_number_increments(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    first = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    second = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    assert first["revision_number"] == 1
    assert second["revision_number"] == 2


def test_rollback_creates_version_1_on_new_asset(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    versions = client.get(
        f"/projects/{project_id}/content-assets/{rollback['id']}/versions",
        headers=auth_headers,
    ).json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1


def test_rollback_reason_saved_in_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(
        client,
        auth_headers,
        project_id,
        source_id,
        version_number=1,
        reason="restore hero section",
    )
    assert rollback["metadata"]["rollback"]["reason"] == "restore hero section"
    assert rollback["metadata"]["rollback"]["source_version_number"] == 1


def test_rollback_reason_max_length_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
        json={"version_number": 1, "reason": "x" * 300},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_missing_source_version_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
        json={"version_number": 99},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_draft_source_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    draft_id = _create_draft(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{draft_id}/rollback-to-version",
        json={"version_number": 1},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_source_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)
    client.post(
        f"/projects/{project_id}/content-assets/{source_id}/archive",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
        json={"version_number": 1},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_rollback_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
        json={"version_number": 1},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_rollback_does_not_auto_approve(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    assert rollback["status"] == "draft"
    assert rollback["approved_version_number"] is None


def test_outbox_event_created_on_rollback(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(client, auth_headers, project_id, source_id, version_number=1)

    events = client.get(
        f"/projects/{project_id}/events",
        params={"event_type": EventType.CONTENT_ASSET_ROLLBACK_REVISION_CREATED.value},
        headers=auth_headers,
    ).json()
    assert len(events) >= 1
    match = next(row for row in events if row["payload"]["revision_asset_id"] == rollback["id"])
    assert match["payload"]["source_asset_id"] == source_id
    assert match["payload"]["source_version_number"] == 1


def test_outbox_failure_does_not_rollback_created_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source_id)

    with patch(
        "app.services.content_asset_service.EventOutboxService"
        ".append_content_asset_rollback_revision_created",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.post(
            f"/projects/{project_id}/content-assets/{source_id}/rollback-to-version",
            json={"version_number": 1},
            headers=auth_headers,
        )
    assert response.status_code == 201
    rollback_id = response.json()["id"]

    detail = client.get(
        f"/projects/{project_id}/content-assets/{rollback_id}",
        headers=auth_headers,
    ).json()
    assert detail["status"] == "draft"
    assert detail["source_asset_id"] == source_id


def test_diff_can_compare_source_version_to_rollback_draft(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(client, auth_headers, project_id, body="old hero")
    client.patch(
        f"/projects/{project_id}/content-assets/{source_id}",
        json={"body": "new hero"},
        headers=auth_headers,
    )
    _approve(client, auth_headers, project_id, source_id)

    rollback = _rollback(client, auth_headers, project_id, source_id, version_number=1)
    v1 = client.get(
        f"/projects/{project_id}/content-assets/{source_id}/versions/1",
        headers=auth_headers,
    ).json()
    assert rollback["body"] == v1["body"]

    diff = client.get(
        f"/projects/{project_id}/content-assets/diff",
        params={"from_asset_id": source_id, "to_asset_id": rollback["id"]},
        headers=auth_headers,
    )
    assert diff.status_code == 200
    assert diff.json()["diff"]["body_changed"] is True

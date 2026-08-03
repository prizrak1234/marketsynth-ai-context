"""Phase 4.6 — read-only content asset diff."""

from __future__ import annotations

from app.marketing.content_diff import (
    build_content_asset_diff,
    build_metadata_diff,
    build_text_diff,
)
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Diff project"},
        headers=headers,
    ).json()["id"]


def _create_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Title",
    body: str = "Body",
    metadata: dict | None = None,
) -> str:
    payload: dict = {"type": "email", "title": title, "body": body}
    if metadata is not None:
        payload["metadata"] = metadata
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_build_text_diff_detects_changes() -> None:
    result = build_text_diff("line one\n", "line two\n")
    assert result["format"] == "unified"
    assert any("line one" in line or "line two" in line for line in result["lines"])


def test_build_text_diff_truncates_long_output() -> None:
    old_text = "\n".join(f"old-{index}" for index in range(500))
    new_text = "\n".join(f"new-{index}" for index in range(500))
    result = build_text_diff(old_text, new_text, max_lines=10)
    assert result["truncated"] is True
    assert len(result["lines"]) == 10


def test_build_metadata_diff_added_removed_changed() -> None:
    diff = build_metadata_diff(
        {"tone": "formal", "channel": "email"},
        {"tone": "casual", "locale": "ru"},
    )
    assert diff["removed"] == {"channel": "email"}
    assert diff["added"] == {"locale": "ru"}
    assert "tone" in diff["changed"]
    assert diff["changed"]["tone"]["old"] == "formal"
    assert diff["changed"]["tone"]["new"] == "casual"


def test_build_metadata_diff_hides_secret_keys() -> None:
    diff = build_metadata_diff(
        {"api_key": "sk-secret", "tone": "formal"},
        {"api_key": "sk-other", "tone": "formal"},
    )
    assert "api_key" not in diff["added"]
    assert "api_key" not in diff["removed"]
    assert "api_key" not in diff["changed"]
    assert diff["added"] == {}
    assert diff["removed"] == {}


def test_build_content_asset_diff_flags_title_and_body() -> None:
    diff = build_content_asset_diff(
        {"title": "A", "body": "one", "metadata": {}},
        {"title": "B", "body": "two", "metadata": {}},
    )
    assert diff["title_changed"] is True
    assert diff["body_changed"] is True
    assert diff["metadata_changed"] is False


def test_version_diff_detects_body_change(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id, body="version one")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "version two"},
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["diff"]["body_changed"] is True
    assert body["from"]["version_number"] == 1
    assert body["to"]["version_number"] == 2


def test_version_diff_detects_title_change(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id, title="First")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"title": "Second"},
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["diff"]["title_changed"] is True


def test_version_diff_detects_metadata_change(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(
        client,
        auth_headers,
        project_id,
        metadata={"tone": "formal"},
    )
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"metadata": {"tone": "casual"}},
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    diff = response.json()["diff"]
    assert diff["metadata_changed"] is True
    assert "tone" in diff["metadata_diff"]["changed"]


def test_version_diff_truncates_long_body(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    old_body = "\n".join(f"old-line-{index}" for index in range(400))
    new_body = "\n".join(f"new-line-{index}" for index in range(400))
    asset_id = _create_draft(client, auth_headers, project_id, body=old_body)
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": new_body},
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body_diff = response.json()["diff"]["body_diff"]
    assert body_diff["truncated"] is True
    assert len(body_diff["lines"]) == 300


def test_missing_version_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 99},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_version_diff_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 1},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_asset_diff_between_two_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    first_id = _create_draft(client, auth_headers, project_id, body="alpha")
    second_id = _create_draft(client, auth_headers, project_id, body="beta")

    response = client.get(
        f"/projects/{project_id}/content-assets/diff",
        params={"from_asset_id": first_id, "to_asset_id": second_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["from"]["asset_id"] == first_id
    assert body["to"]["asset_id"] == second_id
    assert body["diff"]["body_changed"] is True


def test_cross_project_asset_diff_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_a = _project_id(client, auth_headers)
    project_b = _project_id(client, other_auth_headers)
    asset_a = _create_draft(client, auth_headers, project_a)
    asset_b = _create_draft(client, other_auth_headers, project_b)

    response = client.get(
        f"/projects/{project_a}/content-assets/diff",
        params={"from_asset_id": asset_a, "to_asset_id": asset_b},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_revision_diff_compares_source_to_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    source_id = _create_draft(
        client,
        auth_headers,
        project_id,
        title="Approved",
        body="Approved body",
    )
    client.post(
        f"/projects/{project_id}/content-assets/{source_id}/approve",
        headers=auth_headers,
    )
    revision = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json={"body": "Revision body"},
        headers=auth_headers,
    ).json()

    response = client.get(
        f"/projects/{project_id}/content-assets/{revision['id']}/revision-diff",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["from"]["asset_id"] == source_id
    assert body["to"]["asset_id"] == revision["id"]
    assert body["diff"]["body_changed"] is True
    assert "Approved body" in "\n".join(body["diff"]["body_diff"]["lines"])


def test_revision_diff_rejects_non_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id)

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/revision-diff",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_archived_assets_can_be_diffed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id, body="v1")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "v2"},
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_diff_api_does_not_mutate_assets_or_versions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(client, auth_headers, project_id, body="stable")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "changed"},
        headers=auth_headers,
    )

    before_asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    before_versions = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions",
        headers=auth_headers,
    ).json()

    client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )

    after_asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    after_versions = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions",
        headers=auth_headers,
    ).json()

    assert before_asset == after_asset
    assert before_versions == after_versions


def test_metadata_diff_hides_secrets_in_api_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft(
        client,
        auth_headers,
        project_id,
        metadata={"tone": "formal"},
    )
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"metadata": {"tone": "formal", "api_key": "sk-test"}},
        headers=auth_headers,
    )

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    metadata_diff = response.json()["diff"]["metadata_diff"]
    assert "api_key" not in metadata_diff["added"]
    assert "api_key" not in metadata_diff["changed"]

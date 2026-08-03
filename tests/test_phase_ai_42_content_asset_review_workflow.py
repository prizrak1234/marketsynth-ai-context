"""Phase AI.42 — ContentAsset review workflow (draft → review → approved → archived)."""

from __future__ import annotations

import pytest
from app.core.exceptions import InvalidStateError
from app.marketing.asset_policy import validate_content_asset_transition
from app.marketing.contracts import ContentAssetStatus
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "AI.42 Review"},
        headers=headers,
    ).json()["id"]


def _create_draft_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Review asset", "body": "copy"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _submit_review(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str):
    return client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )


def _approve(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str):
    return client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )


def test_draft_cannot_be_approved_directly(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    response = _approve(client, auth_headers, project_id, asset_id)
    assert response.status_code == 409
    body = response.json()
    message = str(body.get("safe_message") or body.get("detail") or "").lower()
    assert "review" in message


def test_draft_can_be_archived(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == ContentAssetStatus.ARCHIVED.value


def test_submit_review_and_approve_flow(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    submitted = _submit_review(client, auth_headers, project_id, asset_id)
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["status"] == ContentAssetStatus.REVIEW.value
    assert body["submitted_for_review_at"] is not None

    approved = _approve(client, auth_headers, project_id, asset_id)
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["status"] == ContentAssetStatus.APPROVED.value
    assert approved_body["approved_at"] is not None
    assert approved_body["approved_version_number"] == approved_body["current_version_number"]


def test_review_can_be_archived(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_review(client, auth_headers, project_id, asset_id)

    archived = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == ContentAssetStatus.ARCHIVED.value


def test_approved_can_be_archived(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_review(client, auth_headers, project_id, asset_id)
    _approve(client, auth_headers, project_id, asset_id)

    archived = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == ContentAssetStatus.ARCHIVED.value


def test_approved_cannot_return_to_review(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_review(client, auth_headers, project_id, asset_id)
    _approve(client, auth_headers, project_id, asset_id)

    again = _submit_review(client, auth_headers, project_id, asset_id)
    assert again.status_code == 409


@pytest.mark.parametrize(
    ("current", "next", "allowed"),
    [
        (ContentAssetStatus.DRAFT, ContentAssetStatus.REVIEW, True),
        (ContentAssetStatus.REVIEW, ContentAssetStatus.APPROVED, True),
        (ContentAssetStatus.REVIEW, ContentAssetStatus.ARCHIVED, True),
        (ContentAssetStatus.APPROVED, ContentAssetStatus.ARCHIVED, True),
        (ContentAssetStatus.DRAFT, ContentAssetStatus.APPROVED, False),
        (ContentAssetStatus.DRAFT, ContentAssetStatus.ARCHIVED, True),
        (ContentAssetStatus.APPROVED, ContentAssetStatus.REVIEW, False),
    ],
)
def test_asset_policy_transitions(
    current: ContentAssetStatus,
    next: ContentAssetStatus,
    allowed: bool,
) -> None:
    if allowed:
        validate_content_asset_transition(current, next)
    else:
        with pytest.raises(InvalidStateError):
            validate_content_asset_transition(current, next)

"""Phase AI.52 — MediaBrief review workflow."""

from __future__ import annotations

import pytest
from app.core.exceptions import InvalidStateError
from app.marketing.media_brief_policy import validate_media_brief_transition
from app.marketing.media_contracts import MediaBriefStatus
from fastapi.testclient import TestClient

from tests.media_workflow import approved_content_asset_id


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "AI.52 Review"}, headers=headers).json()["id"]


def _create_brief(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = approved_content_asset_id(client, headers, project_id)
    created = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    )
    assert created.status_code == 201
    return created.json()["media_brief_id"]


def test_draft_brief_cannot_be_approved_directly(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = _create_brief(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_review_workflow(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = _create_brief(client, auth_headers, project_id)

    submitted = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/submit-review",
        headers=auth_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == MediaBriefStatus.REVIEW.value
    assert submitted.json()["submitted_for_review_at"] is not None

    approved = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == MediaBriefStatus.APPROVED.value
    assert approved.json()["approved_at"] is not None


@pytest.mark.parametrize(
    ("current", "next", "allowed"),
    [
        (MediaBriefStatus.DRAFT, MediaBriefStatus.REVIEW, True),
        (MediaBriefStatus.REVIEW, MediaBriefStatus.APPROVED, True),
        (MediaBriefStatus.DRAFT, MediaBriefStatus.APPROVED, False),
    ],
)
def test_media_brief_policy(
    current: MediaBriefStatus,
    next: MediaBriefStatus,
    allowed: bool,
) -> None:
    if allowed:
        validate_media_brief_transition(current, next)
    else:
        with pytest.raises(InvalidStateError):
            validate_media_brief_transition(current, next)

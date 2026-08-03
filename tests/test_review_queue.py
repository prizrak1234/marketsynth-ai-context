"""Phase 14.0 — human review queue read model."""

from __future__ import annotations

import json

import pytest
from app.domain.review_queue import asset_requires_human_review
from app.marketing.contracts import ContentAssetStatus
from fastapi.testclient import TestClient

LEAK_MARKERS = (
    "plan_payload",
    '"body"',
    "body_preview",
    "version_metadata",
    "super-secret",
    "target_audience",
)


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(client: TestClient, headers: dict[str, str], project_id: str, *, title: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": "active"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _review_queue_url(project_id: str) -> str:
    return f"/projects/{project_id}/review-queue"


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Draft",
    body: str = "super-secret body text",
    campaign_id: str | None = None,
) -> str:
    payload: dict = {"type": "email", "title": title, "body": body}
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    resp = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _submit_review(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> None:
    resp = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _queue_ids(client: TestClient, headers: dict[str, str], project_id: str) -> set[str]:
    resp = client.get(_review_queue_url(project_id), headers=headers)
    assert resp.status_code == 200, resp.text
    return {item["id"] for item in resp.json()["items"]}


def test_assets_in_review_appear_in_review_queue(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ new")
    campaign_id = _campaign(client, auth_headers, project_id, title="Launch")
    asset_id = _create_asset(
        client,
        auth_headers,
        project_id,
        title="Email draft",
        campaign_id=campaign_id,
    )
    assert asset_id not in _queue_ids(client, auth_headers, project_id)
    _submit_review(client, auth_headers, project_id, asset_id)

    resp = client.get(_review_queue_url(project_id), headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["type"] == "content_asset"
    assert item["id"] == asset_id
    assert item["campaign_id"] == campaign_id
    assert item["campaign_title"] == "Launch"
    assert item["status"] == "review"
    assert item["current_version_number"] == 1


def test_approved_assets_disappear_from_review_queue(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ approved")
    asset_id = _create_asset(client, auth_headers, project_id)
    _submit_review(client, auth_headers, project_id, asset_id)
    assert asset_id in _queue_ids(client, auth_headers, project_id)

    approve = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200, approve.text

    assert asset_id not in _queue_ids(client, auth_headers, project_id)


def test_revision_from_approved_asset_appears_in_review_queue(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ revision")
    source_id = _create_asset(client, auth_headers, project_id, title="Source")
    _submit_review(client, auth_headers, project_id, source_id)
    client.post(
        f"/projects/{project_id}/content-assets/{source_id}/approve",
        headers=auth_headers,
    )
    assert source_id not in _queue_ids(client, auth_headers, project_id)

    revision = client.post(
        f"/projects/{project_id}/content-assets/{source_id}/create-revision",
        json={"title": "Revision draft", "body": "new copy"},
        headers=auth_headers,
    )
    assert revision.status_code == 201, revision.text
    revision_id = revision.json()["id"]
    assert revision_id != source_id

    ids = _queue_ids(client, auth_headers, project_id)
    assert revision_id not in ids
    _submit_review(client, auth_headers, project_id, revision_id)
    ids = _queue_ids(client, auth_headers, project_id)
    assert revision_id in ids
    assert source_id not in ids


def test_review_queue_owner_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ mine")
    _create_asset(client, auth_headers, project_id)

    other_project_id = _project_id(client, other_auth_headers, "RQ other")
    denied = client.get(_review_queue_url(other_project_id), headers=auth_headers)
    assert denied.status_code == 404


def test_review_queue_response_has_no_content_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ leaks")
    asset_id = _create_asset(client, auth_headers, project_id, body="super-secret")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "version two secret"},
        headers=auth_headers,
    )
    _submit_review(client, auth_headers, project_id, asset_id)

    resp = client.get(_review_queue_url(project_id), headers=auth_headers)
    assert resp.status_code == 200
    blob = json.dumps(resp.json()).lower()
    item = resp.json()["items"][0]
    assert set(item.keys()) == {
        "type",
        "id",
        "campaign_id",
        "campaign_title",
        "title",
        "status",
        "current_version_number",
        "created_at",
        "updated_at",
    }
    for marker in LEAK_MARKERS:
        assert marker.lower() not in blob


def test_operational_metrics_includes_review_queue_pending_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "RQ metrics")
    a1 = _create_asset(client, auth_headers, project_id, title="A1")
    a2 = _create_asset(client, auth_headers, project_id, title="A2")
    _submit_review(client, auth_headers, project_id, a1)
    _submit_review(client, auth_headers, project_id, a2)

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    )
    assert metrics.status_code == 200, metrics.text
    review_queue = metrics.json()["review_queue"]
    assert review_queue["pending_assets"] == 2

    asset_id = _create_asset(client, auth_headers, project_id, title="A3")
    _submit_review(client, auth_headers, project_id, asset_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    metrics_after = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()["review_queue"]
    assert metrics_after["pending_assets"] == 2


@pytest.mark.parametrize(
    ("status", "current", "approved", "expected"),
    [
        (ContentAssetStatus.REVIEW, 1, None, True),
        (ContentAssetStatus.REVIEW, 3, 2, True),
        (ContentAssetStatus.DRAFT, 2, 2, False),
        (ContentAssetStatus.DRAFT, 1, None, False),
        (ContentAssetStatus.APPROVED, 2, 2, False),
        (ContentAssetStatus.ARCHIVED, 1, None, False),
    ],
)
def test_asset_requires_human_review_predicate(
    status: ContentAssetStatus,
    current: int,
    approved: int | None,
    expected: bool,
) -> None:
    assert (
        asset_requires_human_review(
            status=status,
            current_version_number=current,
            approved_version_number=approved,
        )
        is expected
    )

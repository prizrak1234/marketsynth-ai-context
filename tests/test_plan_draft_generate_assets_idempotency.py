"""Phase 11.1 — plan draft generate-assets idempotency."""

from __future__ import annotations

from app.marketing.plan_draft_asset_mapping import PLAN_DRAFT_GENERATION_PARTIAL_STATE
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
    status: str = "active",
    brief_id: str | None = None,
) -> str:
    payload: dict = {"title": title, "status": status}
    if brief_id is not None:
        payload["brief_id"] = brief_id
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _brief_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _sample_plan_payload(*, item_count: int = 3) -> dict:
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": [
            {
                "title": f"Item {index}",
                "channel": "telegram",
                "format": "text",
                "notes": f"Notes {index}",
            }
            for index in range(item_count)
        ],
    }


def _plan_drafts_url(project_id: str, campaign_id: str) -> str:
    return f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts"


def _generate_assets_url(project_id: str, campaign_id: str, draft_id: str) -> str:
    return f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/generate-assets"


def _create_plan_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    item_count: int = 3,
) -> str:
    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": _sample_plan_payload(item_count=item_count)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_first_call_creates_assets_second_call_is_idempotent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem P1")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)

    first = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["created_count"] == 3
    assert first_body["already_generated"] is False
    first_ids = first_body["asset_ids"]

    second = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["created_count"] == 0
    assert second_body["already_generated"] is True
    assert second_body["asset_ids"] == first_ids

    listed = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    assert len(listed) == 3


def test_partial_existing_assets_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem partial")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=3)

    seeded = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": "Partial seed",
            "body": "seed",
            "campaign_id": campaign_id,
            "metadata": {
                "source_plan_draft_id": draft_id,
                "plan_item_index": 0,
            },
        },
        headers=auth_headers,
    )
    assert seeded.status_code == 201, seeded.text

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == PLAN_DRAFT_GENERATION_PARTIAL_STATE

    listed = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    assert len(listed) == 1


def test_idempotent_replay_preserves_campaign_and_brief_ids(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem brief")
    brief_id = _brief_id(client, auth_headers, project_id)
    campaign_id = _campaign(
        client,
        auth_headers,
        project_id,
        title="C brief",
        brief_id=brief_id,
    )
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        item_count=1,
    )

    client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    replay = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert replay.status_code == 200
    asset_id = replay.json()["asset_ids"][0]
    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["campaign_id"] == campaign_id
    assert asset["brief_id"] == brief_id
    assert asset["status"] == "draft"


def test_idempotent_replay_does_not_create_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem jobs")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=2)

    client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    before = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    after = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    assert len(after) == len(before)


def test_archived_campaign_still_blocks_generate(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem arch camp")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="draft")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=1)
    client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/archive",
        headers=auth_headers,
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_archived_plan_draft_still_blocks_generate(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Idem arch draft")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=1)
    client.post(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/archive",
        headers=auth_headers,
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409

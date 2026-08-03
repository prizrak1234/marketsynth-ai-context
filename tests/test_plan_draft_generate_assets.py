"""Phase 11.0 — generate draft assets from campaign plan draft."""

from __future__ import annotations

from app.marketing.plan_draft_asset_mapping import PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS
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


def _sample_plan_payload(*, item_count: int = 1) -> dict:
    items = [
        {
            "title": f"Item {index}",
            "channel": "telegram",
            "format": "text",
            "scheduled_at": "2026-06-04T15:00:00Z",
            "notes": f"Notes for item {index}",
        }
        for index in range(item_count)
    ]
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": items,
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
    plan_payload: dict | None = None,
) -> str:
    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={
            "title": "June plan",
            "plan_payload": plan_payload or _sample_plan_payload(item_count=3),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_success_creates_draft_assets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets P1")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")

    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)
    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created_count"] == 3
    assert len(body["asset_ids"]) == 3
    assert body["already_generated"] is False

    listed = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assets = listed.json()
    assert len(assets) == 3
    for asset in assets:
        assert asset["status"] == "draft"
        assert asset["campaign_id"] == campaign_id
        assert asset["approved_version_number"] is None


def test_assets_inherit_campaign_id_and_brief_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets brief")
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
        plan_payload=_sample_plan_payload(item_count=1),
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["asset_ids"][0]

    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["campaign_id"] == campaign_id
    assert asset["brief_id"] == brief_id


def test_scheduled_at_stored_only_in_metadata_no_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets schedule")
    campaign_id = _campaign(client, auth_headers, project_id, title="C sched")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload=_sample_plan_payload(item_count=1),
    )

    before_jobs = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["asset_ids"][0]
    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert asset["metadata"]["planned_scheduled_at"] == "2026-06-04T15:00:00Z"
    assert asset["metadata"]["plan_item_index"] == 0
    assert asset["metadata"]["channel"] == "telegram"
    assert asset["body"] == "Notes for item 0"

    after_jobs = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    assert len(after_jobs) == len(before_jobs)


def test_archived_campaign_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets arch camp")
    campaign_id = _campaign(client, auth_headers, project_id, title="C arch", status="draft")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload=_sample_plan_payload(item_count=1),
    )
    client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/archive",
        headers=auth_headers,
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_archived_plan_draft_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets arch draft")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload=_sample_plan_payload(item_count=1),
    )
    client.post(
        f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/archive",
        headers=auth_headers,
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_empty_content_items_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets empty")
    campaign_id = _campaign(client, auth_headers, project_id, title="C empty")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload={
            "goal": "x",
            "target_audience": "y",
            "key_message": "z",
            "content_items": [],
        },
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_more_than_max_items_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets max")
    campaign_id = _campaign(client, auth_headers, project_id, title="C max")
    over_limit = PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS + 1
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload=_sample_plan_payload(item_count=over_limit),
    )

    resp = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_wrong_owner_or_project_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    p1 = _project_id(client, auth_headers, "P1 gen")
    p2 = _project_id(client, other_auth_headers, "P2 gen")
    c1 = _campaign(client, auth_headers, p1, title="C1")
    c2 = _campaign(client, other_auth_headers, p2, title="C2")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        p1,
        c1,
        plan_payload=_sample_plan_payload(item_count=1),
    )

    wrong_campaign = client.post(
        _generate_assets_url(p1, c2, draft_id),
        headers=auth_headers,
    )
    assert wrong_campaign.status_code == 404

    wrong_owner = client.post(
        _generate_assets_url(p1, c1, draft_id),
        headers=other_auth_headers,
    )
    assert wrong_owner.status_code == 404


def test_created_assets_are_not_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gen assets not approved")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_plan_draft(
        client,
        auth_headers,
        project_id,
        campaign_id,
        plan_payload=_sample_plan_payload(item_count=2),
    )
    generated = client.post(
        _generate_assets_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    ).json()

    for asset_id in generated["asset_ids"]:
        asset = client.get(
            f"/projects/{project_id}/content-assets/{asset_id}",
            headers=auth_headers,
        ).json()
        assert asset["status"] == "draft"
        assert asset.get("approved_version_number") is None
        approve = client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
            headers=auth_headers,
        )
        client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/approve",
            headers=auth_headers,
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

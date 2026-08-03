"""Phase 11.2 — plan draft generate-assets readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
import json

import pytest
from fastapi.testclient import TestClient

from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.marketing.plan_draft_asset_mapping import (
    PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS,
    PLAN_DRAFT_GENERATION_PARTIAL_STATE,
    SOURCE_PLAN_DRAFT_ID_METADATA_KEY,
)
from app.tools.registry import get_tool_registry


PHASE_11_FORBIDDEN_TOOLS = frozenset(
    {
        "asset.create_from_plan",
        "content_asset.approve",
        "content_asset.publish",
        "publication_job.create",
        "publication_job.schedule",
    },
)

LEAK_MARKERS = (
    "plan_payload",
    "content_items",
    "target_audience",
    "key_message",
    '"goal"',
    '"notes"',
)


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
    return client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief"},
        headers=headers,
    ).json()["id"]


def _plan_payload(*, item_count: int = 2) -> dict:
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": [
            {
                "title": f"Item {index}",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": f"Secret notes {index}",
            }
            for index in range(item_count)
        ],
    }


def _plan_drafts_url(project_id: str, campaign_id: str) -> str:
    return f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts"


def _generate_url(project_id: str, campaign_id: str, draft_id: str) -> str:
    return f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/generate-assets"


def _create_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    item_count: int = 2,
) -> str:
    resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={"title": "Plan", "plan_payload": _plan_payload(item_count=item_count)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_invariant_generate_assets_tools_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in PHASE_11_FORBIDDEN_TOOLS:
        assert forbidden not in registered
    assert "campaign_plan_draft.generate_assets" in registered
    from app.tools.write_tool_settings import campaign_plan_draft_generate_assets_enabled

    assert campaign_plan_draft_generate_assets_enabled() is False
    assert "content_asset.approve" in FORBIDDEN_AGENT_TOOL_NAMES
    assert "content_asset.publish" in FORBIDDEN_AGENT_TOOL_NAMES


def test_invariant_generate_assets_service_has_no_llm_or_tool_calls() -> None:
    from app.services import campaign_plan_draft_service as plan_service
    from app.services import content_asset_service as asset_service

    plan_source = inspect.getsource(plan_service.CampaignPlanDraftService.generate_assets)
    create_source = inspect.getsource(
        asset_service.ContentAssetService.create_drafts_from_plan_items_in_session,
    )
    combined = (plan_source + create_source).lower()
    for token in ("llm", "langgraph", "openai", "tool_call", "safenoop", "eventoutbox"):
        assert token not in combined


def test_invariant_generate_creates_only_draft_assets_with_inheritance(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 draft only")
    brief_id = _brief_id(client, auth_headers, project_id)
    campaign_id = _campaign(
        client,
        auth_headers,
        project_id,
        title="C1",
        brief_id=brief_id,
    )
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=2)

    resp = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["already_generated"] is False
    assert set(body.keys()) == {"created_count", "asset_ids", "already_generated"}

    for asset_id in body["asset_ids"]:
        asset = client.get(
            f"/projects/{project_id}/content-assets/{asset_id}",
            headers=auth_headers,
        ).json()
        assert asset["status"] == "draft"
        assert asset["campaign_id"] == campaign_id
        assert asset["brief_id"] == brief_id
        assert asset["approved_version_number"] is None
        assert asset["current_version_number"] == 1
        assert asset["metadata"][SOURCE_PLAN_DRAFT_ID_METADATA_KEY] == draft_id
        assert asset["metadata"]["planned_scheduled_at"] == "2026-06-04T15:00:00Z"


def test_invariant_scheduled_at_does_not_create_publication_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 no jobs")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=1)

    before = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    after = client.get(
        f"/projects/{project_id}/publication-jobs",
        headers=auth_headers,
    ).json()
    assert len(after) == len(before)


def test_invariant_repeat_generate_does_not_duplicate(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 idem")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=2)

    first = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    second = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["asset_ids"] == first.json()["asset_ids"]
    assert second.json()["created_count"] == 0

    listed = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers).json()
    assert len(listed) == 2


def test_invariant_partial_state_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 partial")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=3)

    client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": "Seed",
            "body": "x",
            "campaign_id": campaign_id,
            "metadata": {SOURCE_PLAN_DRAFT_ID_METADATA_KEY: draft_id, "plan_item_index": 0},
        },
        headers=auth_headers,
    )

    resp = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == PLAN_DRAFT_GENERATION_PARTIAL_STATE


def test_invariant_archived_campaign_and_draft_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 archived")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1", status="draft")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=1)

    client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/archive",
        headers=auth_headers,
    )
    assert (
        client.post(
            _generate_url(project_id, campaign_id, draft_id),
            headers=auth_headers,
        ).status_code
        == 409
    )

    project_id2 = _project_id(client, auth_headers, "P11 arch draft")
    campaign_id2 = _campaign(client, auth_headers, project_id2, title="C2")
    draft_id2 = _create_draft(client, auth_headers, project_id2, campaign_id2, item_count=1)
    client.post(
        f"{_plan_drafts_url(project_id2, campaign_id2)}/{draft_id2}/archive",
        headers=auth_headers,
    )
    assert (
        client.post(
            _generate_url(project_id2, campaign_id2, draft_id2),
            headers=auth_headers,
        ).status_code
        == 409
    )


def test_invariant_more_than_fifty_items_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 max")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    over = PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS + 1
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=over)

    resp = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    assert resp.status_code == 409


def test_invariant_generate_does_not_auto_approve_or_alter_pinning(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 approve")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=1)
    generated = client.post(
        _generate_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    ).json()
    asset_id = generated["asset_ids"][0]

    before = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert before["approved_version_number"] is None

    approved = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["approved_version_number"] == 1

    replay = client.post(
        _generate_url(project_id, campaign_id, draft_id),
        headers=auth_headers,
    )
    assert replay.status_code == 200
    after = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert after["approved_version_number"] == 1
    assert after["status"] == "approved"


def test_invariant_response_has_no_plan_payload_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "P11 leaks")
    campaign_id = _campaign(client, auth_headers, project_id, title="C1")
    draft_id = _create_draft(client, auth_headers, project_id, campaign_id, item_count=2)

    resp = client.post(_generate_url(project_id, campaign_id, draft_id), headers=auth_headers)
    blob = json.dumps(resp.json()).lower()
    for marker in LEAK_MARKERS:
        assert marker not in blob
    assert "secret notes" not in blob

"""Phase AI.8 — campaign-aware revision context builder and prompts."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from app.agents.revision_context import (
    FORBIDDEN_REVISION_CONTEXT_KEYS,
    REVISION_CONTEXT_MAX_BYTES,
    build_campaign_revision_context,
    build_current_asset_snapshot,
    extract_plan_messaging,
    missing_campaign_revision_context,
    trim_revision_context,
)
from app.marketing.contracts import ContentAssetStatus
from app.prompts.agent_chat_workflow import build_agent_chat_workflow_system_content
from app.schemas.contracts import AgentType, CampaignWorkflowState
from fastapi.testclient import TestClient


def _sample_plan_payload() -> dict:
    return {
        "goal": "Telegram launch",
        "target_audience": "SMB founders",
        "key_message": "Save 20% this week",
        "content_items": [
            {
                "title": "Launch post",
                "channel": "telegram",
                "format": "text",
            },
        ],
    }


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI8 Revision"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={
            "title": "Summer Telegram Push",
            "description": "Drive signups for the SMB offer.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_plan_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={"title": "AI8 plan", "plan_payload": _sample_plan_payload()},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    campaign_id: str,
    title: str,
    body: str,
    status: str = "draft",
) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": title,
            "body": body,
            "campaign_id": campaign_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    asset_id = response.json()["id"]
    if status == "approved":
        approve = client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
            headers=headers,
        )
        client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/approve",
            headers=headers,
        )
        assert approve.status_code == 200, approve.text
    return asset_id


@pytest.mark.asyncio
async def test_context_builder_includes_campaign_workflow_plan_and_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    campaign_id = _create_campaign(client, auth_headers, project_id)
    _create_plan_draft(client, auth_headers, project_id, campaign_id)
    asset_id = _create_asset(
        client,
        auth_headers,
        project_id,
        campaign_id=campaign_id,
        title="Hero post",
        body="Original teaser for founders.",
    )
    _create_asset(
        client,
        auth_headers,
        project_id,
        campaign_id=campaign_id,
        title="Approved sample",
        body="Approved tone reference for the campaign.",
        status="approved",
    )

    owner_id = UUID(
        client.get(f"/projects/{project_id}", headers=auth_headers).json()["owner_id"],
    )
    context = await build_campaign_revision_context(
        db_session,
        owner_id,
        UUID(project_id),
        UUID(campaign_id),
        current_asset_id=UUID(asset_id),
    )

    assert context.get("campaign_missing") is not True
    assert context["campaign_title"] == "Summer Telegram Push"
    assert context["workflow_state"]
    assert context["target_audience"] == "SMB founders"
    assert context["key_message"] == "Save 20% this week"
    assert context["channel"] == "telegram"
    assert context["current_asset"]["asset_id"] == asset_id
    assert len(context["approved_assets_examples"]) >= 1


def test_extract_plan_messaging_without_full_payload_leak() -> None:
    signals = extract_plan_messaging(_sample_plan_payload())
    assert signals["key_message"] == "Save 20% this week"
    encoded = json.dumps(signals)
    assert "content_items" not in encoded
    assert "plan_payload" not in encoded


def test_trim_revision_context_enforces_size_limit() -> None:
    huge = {
        "campaign_title": "X",
        "campaign_description": "Y" * 5000,
        "workflow_state": CampaignWorkflowState.ASSETS_GENERATED.value,
        "target_audience": "audience " * 500,
        "key_message": "message " * 500,
        "channel": "telegram",
        "approved_assets_examples": [
            {
                "asset_id": str(uuid4()),
                "title": "Example",
                "body_preview": "body " * 800,
            }
            for _ in range(10)
        ],
        "current_asset": {
            "asset_id": str(uuid4()),
            "body_preview": "current " * 800,
        },
        "campaign_history": {"assets_total": 99},
    }
    trimmed = trim_revision_context(huge)
    size = len(json.dumps(trimmed, ensure_ascii=True).encode("utf-8"))
    assert size <= REVISION_CONTEXT_MAX_BYTES
    assert trimmed.get("context_truncated") is True


def test_missing_campaign_revision_context_fallback() -> None:
    context = missing_campaign_revision_context(workflow_state="planning")
    assert context["campaign_missing"] is True
    assert context["workflow_state"] == "planning"
    assert context["approved_assets_examples"] == []


@pytest.mark.asyncio
async def test_missing_campaign_row_returns_fallback(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    owner_id = UUID(
        client.get(f"/projects/{project_id}", headers=auth_headers).json()["owner_id"],
    )
    context = await build_campaign_revision_context(
        db_session,
        owner_id,
        UUID(project_id),
        uuid4(),
    )
    assert context["campaign_missing"] is True


def test_revision_context_has_no_forbidden_leaks() -> None:
    context = {
        "campaign_title": "T",
        "campaign_description": "D",
        "workflow_state": "assets_generated",
        "target_audience": "A",
        "key_message": "K",
        "channel": "telegram",
        "approved_assets_examples": [],
        "campaign_history": {"assets_total": 1},
    }
    encoded = json.dumps(context)
    for forbidden in FORBIDDEN_REVISION_CONTEXT_KEYS:
        assert forbidden not in encoded


@pytest.mark.asyncio
async def test_builder_excludes_delivery_and_plan_payload_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    campaign_id = _create_campaign(client, auth_headers, project_id)
    _create_plan_draft(client, auth_headers, project_id, campaign_id)

    owner_id = UUID(
        client.get(f"/projects/{project_id}", headers=auth_headers).json()["owner_id"],
    )
    context = await build_campaign_revision_context(
        db_session,
        owner_id,
        UUID(project_id),
        UUID(campaign_id),
    )
    encoded = json.dumps(context)
    assert "plan_payload" not in encoded
    assert "content_items" not in encoded
    assert "delivery_logs" not in encoded
    assert "recent_jobs" not in encoded
    assert "channel_config" not in encoded
    assert "api_key" not in encoded.lower()


def test_revision_prompt_includes_workflow_title_and_key_message() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
        "next_recommended_action": "review_assets",
        "pending_review_assets": 2,
        "revision_context": {
            "campaign_title": "Summer Telegram Push",
            "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
            "key_message": "Save 20% this week",
            "target_audience": "SMB founders",
            "channel": "telegram",
        },
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        revision_tools=True,
        agent_type=AgentType.COPYWRITER,
    )
    assert "workflow_state" in content
    assert "Summer Telegram Push" in content
    assert "Save 20% this week" in content
    assert "Campaign-aware copywriter" in content
    assert "Do not invent facts" in content


def test_current_asset_snapshot_uses_body_preview_not_full_body() -> None:
    from types import SimpleNamespace

    row = SimpleNamespace(
        id=uuid4(),
        title="Post",
        body="x" * 5000,
        status=type("S", (), {"value": ContentAssetStatus.DRAFT.value})(),
        asset_type=type("T", (), {"value": "telegram_post"})(),
        asset_metadata={"channel": "telegram"},
        current_version_number=1,
    )
    snapshot = build_current_asset_snapshot(row, default_channel="telegram")
    assert len(snapshot["body_preview"]) < 500
    assert "body" not in snapshot

"""Phase AI.8.1 — campaign-aware revision context readiness invariants (freeze guard)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.agents.revision_context import (
    APPROVED_EXAMPLES_MAX,
    FORBIDDEN_REVISION_CONTEXT_KEYS,
    REVISION_CONTEXT_MAX_BYTES,
    build_approved_asset_example,
    build_campaign_history_summary,
    build_campaign_revision_context,
    missing_campaign_revision_context,
    trim_revision_context,
)
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.marketing.contracts import ContentAssetStatus
from app.prompts.agent_chat_workflow import (
    _AGENT_CHAT_CAMPAIGN_AWARE_COPYWRITER_RULES,
    build_agent_chat_workflow_system_content,
)
from app.schemas.contracts import AgentType, CampaignWorkflowState
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES,
    AGENT_CHAT_REVISION_WRITE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    list_tools_for_agent_chat,
)
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
)
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

CONTEXT_LEAK_MARKERS = (
    "plan_payload",
    "content_items",
    "channel_config",
    "delivery_logs",
    "recent_jobs",
    "campaign_metadata",
    '"body":',
    "secret_token",
)

APPROVED_EXAMPLE_ALLOWED_KEYS = frozenset(
    {"asset_id", "title", "channel", "body_preview"},
)

CAMPAIGN_HISTORY_ALLOWED_KEYS = frozenset(
    {
        "assets_total",
        "assets_draft",
        "assets_approved",
        "assets_archived",
        "jobs_total",
        "jobs_scheduled",
        "jobs_succeeded",
    },
)

CURRENT_ASSET_ALLOWED_KEYS = frozenset(
    {
        "asset_id",
        "title",
        "status",
        "type",
        "channel",
        "body_preview",
        "current_version_number",
    },
)

AI_8_CHAT_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)

COPYWRITER_PROMPT_MARKERS = (
    "Campaign-aware copywriter",
    "key_message",
    "Do not invent facts",
    "Campaign revision context",
)

REVISION_REQUIRED_FLAGS = (
    "AGENT_WRITE_TOOLS_ENABLED",
    "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
    "AGENT_CHAT_TOOLS_ENABLED",
    "TOOLS_PROVIDER_ENABLED",
)


@pytest.fixture
def all_revision_chat_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in REVISION_REQUIRED_FLAGS:
        monkeypatch.setenv(flag, "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _encoded_size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8"))


def _assert_context_within_limit(context: dict) -> None:
    assert _encoded_size(context) <= REVISION_CONTEXT_MAX_BYTES
    assert REVISION_CONTEXT_MAX_BYTES == 8192


def _assert_no_context_leaks(context: dict) -> None:
    encoded = json.dumps(context)
    for marker in CONTEXT_LEAK_MARKERS:
        assert marker not in encoded
    for forbidden in FORBIDDEN_REVISION_CONTEXT_KEYS:
        assert forbidden not in context


def _sample_plan_payload() -> dict:
    return {
        "goal": "Telegram launch",
        "target_audience": "SMB founders",
        "key_message": "Save 20% this week",
        "content_items": [
            {"title": "Post", "channel": "telegram", "format": "text"},
        ],
    }


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI8.1 inv"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_campaign(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/campaigns",
        json={
            "title": "Summer Push",
            "description": "Offer for SMB.",
            "campaign_metadata": {"channel_config": {"bot_token": "secret_token"}},
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
) -> None:
    response = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _create_and_approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    title: str,
    body: str,
) -> str:
    created = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "telegram_post",
            "title": title,
            "body": body,
            "campaign_id": campaign_id,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]
    submitted = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    return asset_id


def test_invariant_revision_context_max_bytes_constant() -> None:
    assert REVISION_CONTEXT_MAX_BYTES == 8192
    assert APPROVED_EXAMPLES_MAX == 3


def test_invariant_trimmed_context_respects_8kb_limit() -> None:
    huge = {
        "campaign_title": "T",
        "campaign_description": "D" * 6000,
        "workflow_state": CampaignWorkflowState.ASSETS_GENERATED.value,
        "target_audience": "A" * 800,
        "key_message": "K" * 800,
        "channel": "telegram",
        "approved_assets_examples": [
            {
                "asset_id": str(uuid4()),
                "title": "E",
                "channel": "telegram",
                "body_preview": "p" * 2000,
            }
            for _ in range(10)
        ],
        "current_asset": {
            "asset_id": str(uuid4()),
            "body_preview": "c" * 2000,
        },
        "campaign_history": {"assets_total": 5},
    }
    trimmed = trim_revision_context(huge)
    _assert_context_within_limit(trimmed)


@pytest.mark.asyncio
async def test_invariant_built_context_within_8kb_no_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    campaign_id = _create_campaign(client, auth_headers, project_id)
    _create_plan_draft(client, auth_headers, project_id, campaign_id)
    for index in range(4):
        _create_and_approve_asset(
            client,
            auth_headers,
            project_id,
            campaign_id,
            title=f"Approved {index}",
            body=f"Approved body {index} " + ("x" * 400),
        )

    owner_id = UUID(
        client.get(f"/projects/{project_id}", headers=auth_headers).json()["owner_id"],
    )
    context = await build_campaign_revision_context(
        db_session,
        owner_id,
        UUID(project_id),
        UUID(campaign_id),
    )
    _assert_context_within_limit(context)
    _assert_no_context_leaks(context)
    assert context["key_message"] == "Save 20% this week"
    assert len(context["approved_assets_examples"]) <= APPROVED_EXAMPLES_MAX


def test_invariant_approved_examples_preview_only_max_three() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        title="Sample",
        body="Full body must not appear in revision context output.",
        asset_type=type("T", (), {"value": "telegram_post"})(),
        asset_metadata={},
    )
    example = build_approved_asset_example(row, default_channel="telegram")
    assert set(example.keys()) == APPROVED_EXAMPLE_ALLOWED_KEYS
    assert "body" not in example
    assert len(example["body_preview"]) <= 320


def test_invariant_campaign_history_counts_only() -> None:
    counts = SimpleNamespace(
        assets_total=10,
        assets_draft=3,
        assets_approved=5,
        assets_archived=2,
        jobs_total=4,
        jobs_scheduled=1,
        jobs_succeeded=2,
        jobs_failed=99,
    )
    history = build_campaign_history_summary(counts)
    assert set(history.keys()) <= CAMPAIGN_HISTORY_ALLOWED_KEYS
    assert all(isinstance(value, int) for value in history.values())
    assert "jobs_failed" not in history
    encoded = json.dumps(history)
    assert "delivery" not in encoded
    assert "recent_jobs" not in encoded


def test_invariant_missing_campaign_fallback_within_limit() -> None:
    context = missing_campaign_revision_context(workflow_state="planning")
    assert context["campaign_missing"] is True
    assert context["workflow_state"] == "planning"
    assert context["approved_assets_examples"] == []
    _assert_context_within_limit(context)
    _assert_no_context_leaks(context)


@pytest.mark.asyncio
async def test_invariant_unknown_campaign_id_returns_fallback(
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
    _assert_context_within_limit(context)


def test_invariant_current_asset_snapshot_has_no_full_body() -> None:
    from app.agents.revision_context import build_current_asset_snapshot

    row = SimpleNamespace(
        id=uuid4(),
        title="Draft",
        body="x" * 8000,
        status=type("S", (), {"value": ContentAssetStatus.DRAFT.value})(),
        asset_type=type("T", (), {"value": "telegram_post"})(),
        asset_metadata={},
        current_version_number=2,
    )
    snapshot = build_current_asset_snapshot(row, default_channel="telegram")
    assert set(snapshot.keys()) == CURRENT_ASSET_ALLOWED_KEYS
    assert "body" not in snapshot
    assert len(snapshot["body_preview"]) < 500


def test_invariant_copywriter_prompt_contains_campaign_aware_rules() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
        "next_recommended_action": "review_assets",
        "pending_review_assets": 1,
        "revision_context": {
            "campaign_title": "Summer Push",
            "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
            "key_message": "Save 20% this week",
        },
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        revision_tools=True,
        agent_type=AgentType.COPYWRITER,
    )
    for marker in COPYWRITER_PROMPT_MARKERS:
        assert marker in content
    assert _AGENT_CHAT_CAMPAIGN_AWARE_COPYWRITER_RULES.splitlines()[0] in content
    assert "Summer Push" in content


def test_invariant_non_copywriter_revision_prompt_omits_campaign_aware_block() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.ASSETS_GENERATED.value,
        "next_recommended_action": "review",
        "pending_review_assets": 0,
        "revision_context": {"campaign_title": "T", "key_message": "K"},
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        revision_tools=True,
        agent_type=AgentType.CONTENT_PLANNER,
    )
    assert "Campaign-aware copywriter" not in content


def test_invariant_ai8_added_no_new_write_tools() -> None:
    assert AGENT_CHAT_REVISION_WRITE_TOOL_NAMES == frozenset(
        {CONTENT_ASSET_CREATE_REVISION_TOOL_NAME},
    )
    write_tools_in_profile = {
        name
        for name in AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES
        if name.endswith(".create")
        or name.endswith(".create_revision")
        or name.endswith(".generate_assets")
        or name.endswith(".approve")
        or name.endswith(".publish")
        or name.endswith(".schedule")
    }
    assert write_tools_in_profile == {CONTENT_ASSET_CREATE_REVISION_TOOL_NAME}


def test_invariant_revision_profile_includes_overview_read_only(
    all_revision_chat_flags_on: None,
) -> None:
    names = {
        tool.name
        for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER)
    }
    assert MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME in names
    assert names == set(AGENT_CHAT_REVISION_PROFILE_TOOL_NAMES)


def test_invariant_chat_profile_still_forbids_approve_schedule_publish(
    all_revision_chat_flags_on: None,
) -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in AI_8_CHAT_FORBIDDEN_TOOL_NAMES:
        assert forbidden not in AGENT_CHAT_TOOL_NAMES
        assert forbidden not in {
            tool.name
            for tool in list_tools_for_agent_chat(get_tool_registry(), AgentType.COPYWRITER)
        }
    for name in ("content_asset.approve", "content_asset.publish"):
        assert name in FORBIDDEN_AGENT_TOOL_NAMES
    for name in ("content_asset.schedule", "publication_job.schedule", "publication_job.create"):
        assert name not in registered


def test_invariant_run_input_carries_revision_context_when_provided() -> None:
    revision_context = {
        "campaign_title": "T",
        "workflow_state": "assets_generated",
        "key_message": "K",
    }
    payload = build_agent_chat_run_input_payload(
        prompt="Improve",
        project_id=uuid4(),
        workflow_context={
            "campaign_id": str(uuid4()),
            "workflow_state": "assets_generated",
            "next_recommended_action": "review",
            "pending_review_assets": 0,
        },
        revision_context=revision_context,
    )
    agent_chat = payload.get("agent_chat") or {}
    assert agent_chat.get("revision_context") == revision_context
    _assert_no_context_leaks(agent_chat["revision_context"])

"""Phase 13.0 — campaign execution workflow read model."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.db.models.publishing import PublicationJobTable
from app.domain.campaign_workflow import (
    CampaignWorkflowInput,
    WorkflowAssetFacts,
    compute_campaign_workflow,
)
from app.marketing.contracts import ContentAssetStatus
from app.publishing.contracts import PublicationJobStatus
from app.schemas.contracts import (
    CampaignWorkflowRecommendedAction,
    CampaignWorkflowState,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

LEAK_MARKERS = (
    "plan_payload",
    "target_audience",
    "key_message",
    "Secret notes",
    "super-secret-body",
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


def _workflow_url(project_id: str, campaign_id: str) -> str:
    return f"/projects/{project_id}/campaigns/{campaign_id}/workflow"


def _sample_plan_payload(*, item_count: int = 2) -> dict:
    items = [
        {
            "title": f"Item {index}",
            "channel": "telegram",
            "format": "text",
            "scheduled_at": "2026-06-04T15:00:00Z",
            "notes": f"Secret notes {index}",
        }
        for index in range(item_count)
    ]
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": items,
    }


def _create_plan_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    item_count: int = 2,
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={"title": "Plan", "plan_payload": _sample_plan_payload(item_count=item_count)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _generate_assets(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    draft_id: str,
) -> list[str]:
    resp = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=headers,
    )
    assert resp.status_code in {200, 201}, resp.text
    return resp.json()["asset_ids"]


def _patch_asset_body(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
    body: str,
) -> None:
    resp = client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": body},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> None:
    resp =     client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=headers,
    ).json()["id"]


def _schedule_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
) -> str:
    payload = {
        "asset_id": asset_id,
        "channel_id": channel_id,
        "scheduled_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat().replace(
            "+00:00",
            "Z",
        ),
    }
    resp = client.post(
        f"/projects/{project_id}/publication-jobs",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _mark_job_succeeded(db_session: AsyncSession, job_id: str) -> None:
    row = await db_session.get(PublicationJobTable, UUID(job_id))
    assert row is not None
    row.status = PublicationJobStatus.SUCCEEDED
    db_session.add(row)
    await db_session.commit()


def test_compute_planning_domain() -> None:
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(),
            succeeded_job_asset_ids=frozenset(),
            pending_review_assets=0,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.PLANNING
    assert result.next_recommended_action == CampaignWorkflowRecommendedAction.CREATE_PLAN_DRAFT


def test_workflow_planning(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF planning")
    campaign_id = _campaign(client, auth_headers, project_id, title="C planning")

    resp = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workflow_state"] == "planning"
    assert body["counts"]["plan_drafts"] == 0
    assert body["counts"]["assets_total"] == 0
    assert body["next_recommended_action"] == "create_plan_draft"


def test_workflow_plan_ready(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF plan ready")
    campaign_id = _campaign(client, auth_headers, project_id, title="C plan ready")
    _create_plan_draft(client, auth_headers, project_id, campaign_id)

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "plan_ready"
    assert body["counts"]["plan_drafts"] == 1
    assert body["counts"]["assets_total"] == 0
    assert body["next_recommended_action"] == "generate_assets"


def test_workflow_assets_generated(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF assets gen")
    campaign_id = _campaign(client, auth_headers, project_id, title="C assets")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    assert len(asset_ids) == 2

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "ready_for_review"
    assert body["counts"]["assets_total"] == 2
    assert body["counts"]["assets_draft"] == 2
    assert body["counts"]["assets_approved"] == 0
    assert body["counts"]["pending_review_assets"] == 2
    assert body["next_recommended_action"] == "human_review_required"


def test_workflow_content_in_revision(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF revising")
    campaign_id = _campaign(client, auth_headers, project_id, title="C revising")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=2)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    _patch_asset_body(client, auth_headers, project_id, asset_ids[0], "revised copy v2")

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "ready_for_review"
    assert body["counts"]["assets_draft"] == 2
    assert body["counts"]["pending_review_assets"] == 2
    assert body["next_recommended_action"] == "human_review_required"


def test_workflow_ready_for_review(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF ready review")
    campaign_id = _campaign(client, auth_headers, project_id, title="C ready")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=2)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    for asset_id in asset_ids:
        _patch_asset_body(client, auth_headers, project_id, asset_id, f"final {asset_id}")

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "ready_for_review"
    assert body["counts"]["pending_review_assets"] == 2
    assert body["next_recommended_action"] == "human_review_required"


def test_workflow_pending_review_priority_over_approved_for_publication(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF priority")
    campaign_id = _campaign(client, auth_headers, project_id, title="C priority")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=2)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    _approve_asset(client, auth_headers, project_id, asset_ids[0])

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "ready_for_review"
    assert body["counts"]["pending_review_assets"] == 1
    assert body["counts"]["assets_approved"] == 1
    assert body["next_recommended_action"] == "human_review_required"


def test_workflow_approved_for_publication(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF approved")
    campaign_id = _campaign(client, auth_headers, project_id, title="C approved")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=1)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    _approve_asset(client, auth_headers, project_id, asset_ids[0])

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "approved_for_publication"
    assert body["counts"]["assets_approved"] == 1
    assert body["next_recommended_action"] == "schedule_publication"


@pytest.mark.asyncio
async def test_workflow_completed(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF completed")
    campaign_id = _campaign(client, auth_headers, project_id, title="C done")
    channel_id = _custom_channel(client, auth_headers, project_id)
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id, item_count=1)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    _approve_asset(client, auth_headers, project_id, asset_ids[0])
    job_id = _schedule_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_ids[0],
        channel_id=channel_id,
    )
    await _mark_job_succeeded(db_session, job_id)

    body = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers).json()
    assert body["workflow_state"] == "completed"
    assert body["next_recommended_action"] == "none"


def test_workflow_owner_scope_denied(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF mine")
    other_project_id = _project_id(client, other_auth_headers, "WF other")
    other_campaign_id = _campaign(client, other_auth_headers, other_project_id, title="C other")

    denied = client.get(
        _workflow_url(project_id, other_campaign_id),
        headers=auth_headers,
    )
    assert denied.status_code == 404


def test_workflow_response_has_no_content_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "WF leaks")
    campaign_id = _campaign(client, auth_headers, project_id, title="C leaks")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)
    asset_ids = _generate_assets(client, auth_headers, project_id, campaign_id, draft_id)
    _patch_asset_body(client, auth_headers, project_id, asset_ids[0], "super-secret-body")

    resp = client.get(_workflow_url(project_id, campaign_id), headers=auth_headers)
    assert resp.status_code == 200
    blob = json.dumps(resp.json()).lower()
    assert set(resp.json().keys()) == {
        "campaign_id",
        "workflow_state",
        "counts",
        "next_recommended_action",
    }
    assert set(resp.json()["counts"].keys()) == {
        "plan_drafts",
        "assets_total",
        "assets_approved",
        "assets_draft",
        "pending_review_assets",
    }
    for marker in LEAK_MARKERS:
        assert marker.lower() not in blob


def test_workflow_ready_for_review_when_pending_review_assets() -> None:
    asset = WorkflowAssetFacts(
        asset_id=uuid4(),
        status=ContentAssetStatus.DRAFT,
        current_version_number=1,
        source_asset_id=None,
    )
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(asset,),
            succeeded_job_asset_ids=frozenset(),
            pending_review_assets=1,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.READY_FOR_REVIEW
    assert result.counts.pending_review_assets == 1
    assert result.next_recommended_action == CampaignWorkflowRecommendedAction.HUMAN_REVIEW_REQUIRED


def test_workflow_pending_review_over_approved_for_publication() -> None:
    approved = WorkflowAssetFacts(
        asset_id=uuid4(),
        status=ContentAssetStatus.APPROVED,
        current_version_number=1,
        source_asset_id=None,
    )
    draft = WorkflowAssetFacts(
        asset_id=uuid4(),
        status=ContentAssetStatus.DRAFT,
        current_version_number=1,
        source_asset_id=None,
    )
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(approved, draft),
            succeeded_job_asset_ids=frozenset(),
            pending_review_assets=1,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.READY_FOR_REVIEW
    assert result.next_recommended_action == CampaignWorkflowRecommendedAction.HUMAN_REVIEW_REQUIRED


def test_workflow_completed_over_pending_review() -> None:
    asset_id = uuid4()
    asset = WorkflowAssetFacts(
        asset_id=asset_id,
        status=ContentAssetStatus.APPROVED,
        current_version_number=1,
        source_asset_id=None,
    )
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(asset,),
            succeeded_job_asset_ids=frozenset({asset_id}),
            pending_review_assets=3,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.COMPLETED
    assert result.next_recommended_action == CampaignWorkflowRecommendedAction.NONE


def test_workflow_content_in_revision_when_no_pending_review_queue() -> None:
    asset_a = WorkflowAssetFacts(
        asset_id=uuid4(),
        status=ContentAssetStatus.DRAFT,
        current_version_number=2,
        source_asset_id=None,
    )
    asset_b = WorkflowAssetFacts(
        asset_id=uuid4(),
        status=ContentAssetStatus.DRAFT,
        current_version_number=1,
        source_asset_id=None,
    )
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=1,
            assets=(asset_a, asset_b),
            succeeded_job_asset_ids=frozenset(),
            pending_review_assets=0,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.CONTENT_IN_REVISION

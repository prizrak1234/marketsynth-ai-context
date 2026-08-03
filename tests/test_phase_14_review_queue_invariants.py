"""Phase 14.3 — review queue readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.api import projects as projects_routes
from app.domain import campaign_workflow as campaign_workflow_domain
from app.domain.review_queue import asset_requires_human_review
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import (
    AgentType,
    CampaignWorkflowRecommendedAction,
    CampaignWorkflowState,
    ReviewQueueItemType,
)
from app.schemas.marketing_campaigns import CampaignWorkflowCounts, CampaignWorkflowResponse
from app.schemas.operational_metrics import OperationalMetricsResponse
from app.schemas.review_queue import ReviewQueueItem
from app.services import campaign_workflow_service as campaign_workflow_service_module
from app.services import review_queue_service as review_queue_service_module
from app.tools.marketing_tools import format_marketing_campaign_workflow_compact
from app.tools.permissions import (
    REAL_READ_ONLY_EXECUTABLE_TOOLS,
    WRITE_TOOL_NAMES,
    is_real_read_only_executable,
)
from app.tools.registry import REVIEW_QUEUE_LIST_TOOL, get_tool_registry
from app.tools.review_queue_tools import (
    REVIEW_QUEUE_LIST_TOOL_NAME,
    format_review_queue_list_compact,
)
from app.tools.write_tool_settings import is_real_write_executable
from app.domain.campaign_workflow import (
    CampaignWorkflowInput,
    WorkflowAssetFacts,
    compute_campaign_workflow,
)

PHASE_14_FORBIDDEN_AGENT_TOOLS = frozenset(
    {
        "review_queue.approve",
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)

REVIEW_QUEUE_TOOL_ALLOWED = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
        AgentType.ANALYST,
    },
)

REVIEW_QUEUE_TOOL_DENIED = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
    },
)

COMPACT_QUEUE_ITEM_KEYS = frozenset(
    {
        "type",
        "id",
        "campaign_id",
        "campaign_title",
        "title",
        "status",
        "current_version_number",
        "updated_at",
    },
)

LEAK_MARKERS = (
    "plan_payload",
    "body",
    "version",
    "channel_config",
    "delivery",
    "campaign_metadata",
)


def test_invariant_review_queue_api_route_is_get_only() -> None:
    module_source = inspect.getsource(projects_routes)
    assert '@router.get("/{project_id}/review-queue"' in module_source
    assert '@router.post("/{project_id}/review-queue"' not in module_source
    assert '@router.patch("/{project_id}/review-queue"' not in module_source
    assert '@router.put("/{project_id}/review-queue"' not in module_source
    assert '@router.delete("/{project_id}/review-queue"' not in module_source


def test_invariant_review_queue_list_tool_registered_as_read_only() -> None:
    assert REVIEW_QUEUE_LIST_TOOL.metadata.get("access_mode") == "read_only"
    assert REVIEW_QUEUE_LIST_TOOL.metadata.get("execution_mode") == "read_only"
    assert is_real_read_only_executable(REVIEW_QUEUE_LIST_TOOL_NAME)
    assert REVIEW_QUEUE_LIST_TOOL_NAME in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert REVIEW_QUEUE_LIST_TOOL_NAME not in WRITE_TOOL_NAMES
    assert not is_real_write_executable(REVIEW_QUEUE_LIST_TOOL_NAME)


def test_invariant_review_queue_approve_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    assert "review_queue.approve" not in registered
    for forbidden in PHASE_14_FORBIDDEN_AGENT_TOOLS:
        assert forbidden not in registered
    assert "content_asset.approve" in FORBIDDEN_AGENT_TOOL_NAMES


@pytest.mark.parametrize(
    ("status", "current", "approved", "expected"),
    [
        (ContentAssetStatus.REVIEW, 1, None, True),
        (ContentAssetStatus.REVIEW, 4, 3, True),
        (ContentAssetStatus.DRAFT, 1, None, False),
        (ContentAssetStatus.DRAFT, 4, 3, False),
        (ContentAssetStatus.APPROVED, 2, 2, False),
        (ContentAssetStatus.ARCHIVED, 1, None, False),
    ],
)
def test_invariant_pending_review_predicate(
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


def test_invariant_workflow_ready_for_review_when_pending_review_assets() -> None:
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(
                WorkflowAssetFacts(
                    asset_id=uuid4(),
                    status=ContentAssetStatus.APPROVED,
                    current_version_number=1,
                    source_asset_id=None,
                ),
            ),
            succeeded_job_asset_ids=frozenset(),
            pending_review_assets=2,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.READY_FOR_REVIEW
    assert result.counts.pending_review_assets == 2
    assert result.next_recommended_action == CampaignWorkflowRecommendedAction.HUMAN_REVIEW_REQUIRED


def test_invariant_workflow_completed_over_pending_review() -> None:
    asset_id = uuid4()
    result = compute_campaign_workflow(
        CampaignWorkflowInput(
            plan_drafts_count=0,
            assets=(
                WorkflowAssetFacts(
                    asset_id=asset_id,
                    status=ContentAssetStatus.APPROVED,
                    current_version_number=1,
                    source_asset_id=None,
                ),
            ),
            succeeded_job_asset_ids=frozenset({asset_id}),
            pending_review_assets=5,
        ),
    )
    assert result.workflow_state == CampaignWorkflowState.COMPLETED


def test_invariant_workflow_tool_output_includes_pending_review_assets() -> None:
    workflow = CampaignWorkflowResponse(
        campaign_id=uuid4(),
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW,
        counts=CampaignWorkflowCounts(pending_review_assets=3),
        next_recommended_action=CampaignWorkflowRecommendedAction.HUMAN_REVIEW_REQUIRED,
    )
    payload = format_marketing_campaign_workflow_compact(workflow)
    assert payload["counts"]["pending_review_assets"] == 3
    assert "pending_review_assets" in payload["counts"]


@pytest.mark.parametrize("agent_type", sorted(REVIEW_QUEUE_TOOL_ALLOWED, key=lambda t: t.value))
def test_invariant_review_queue_tool_allowlist(agent_type: AgentType) -> None:
    names = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert REVIEW_QUEUE_LIST_TOOL_NAME in names


@pytest.mark.parametrize("agent_type", sorted(REVIEW_QUEUE_TOOL_DENIED, key=lambda t: t.value))
def test_invariant_review_queue_tool_denylist(agent_type: AgentType) -> None:
    names = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert REVIEW_QUEUE_LIST_TOOL_NAME not in names


def test_invariant_compact_review_queue_tool_output_no_leaks() -> None:
    now = datetime.now(tz=UTC)
    items = [
        ReviewQueueItem(
            type=ReviewQueueItemType.CONTENT_ASSET,
            id=uuid4(),
            campaign_id=uuid4(),
            campaign_title="Launch",
            title="Email",
            status=ContentAssetStatus.DRAFT,
            current_version_number=2,
            created_at=now,
            updated_at=now,
        ),
    ]
    payload = format_review_queue_list_compact(items, count=1)
    assert set(payload.keys()) == {"items", "count"}
    assert set(payload["items"][0].keys()) == COMPACT_QUEUE_ITEM_KEYS
    blob = str(payload).lower()
    for marker in LEAK_MARKERS:
        if marker == "body":
            assert '"body"' not in blob
            assert "body_preview" not in blob
        elif marker == "version":
            assert "versions" not in blob
            assert "version_metadata" not in blob
            assert "version body" not in blob
        else:
            assert marker not in blob


def test_invariant_review_queue_service_is_read_only() -> None:
    source = inspect.getsource(review_queue_service_module.ReviewQueueService)
    for forbidden in (".add(", ".commit(", ".delete(", ".flush(", "session.merge"):
        assert forbidden not in source
    assert "get_queue" in source
    assert "list_for_tool" in source
    assert "count_pending_assets" in source


def test_invariant_workflow_service_uses_review_queue_count() -> None:
    domain_source = inspect.getsource(campaign_workflow_domain)
    assert "pending_review_assets" in domain_source
    service_source = inspect.getsource(campaign_workflow_service_module.CampaignWorkflowService)
    assert "ReviewQueueService" in service_source
    assert "count_pending_assets" in service_source


def test_invariant_operational_metrics_includes_review_queue() -> None:
    fields = OperationalMetricsResponse.model_fields
    assert "review_queue" in fields

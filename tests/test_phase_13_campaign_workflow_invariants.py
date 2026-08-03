"""Phase 13.2 — campaign workflow diagnostics readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
from uuid import uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.api.routes import marketing_campaigns as marketing_campaign_routes
from app.domain import campaign_workflow as campaign_workflow_domain
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS, _CAMPAIGN_WORKFLOW_GUIDANCE
from app.schemas.contracts import AgentType, CampaignWorkflowState
from app.schemas.marketing_campaigns import CampaignWorkflowCounts, CampaignWorkflowResponse
from app.services import campaign_workflow_service as campaign_workflow_service_module
from app.tools.marketing_tools import (
    MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
    format_marketing_campaign_workflow_compact,
)
from app.tools.permissions import (
    REAL_READ_ONLY_EXECUTABLE_TOOLS,
    WRITE_TOOL_NAMES,
    is_real_read_only_executable,
)
from app.tools.registry import MARKETING_CAMPAIGN_WORKFLOW_TOOL, get_tool_registry
from app.tools.write_tool_settings import is_real_write_executable

PHASE_13_FORBIDDEN_AGENT_TOOLS = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)

WORKFLOW_TOOL_ALLOWED = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
        AgentType.ANALYST,
    },
)

WORKFLOW_TOOL_DENIED = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
    },
)

COMPACT_WORKFLOW_OUTPUT_KEYS = frozenset(
    {
        "campaign_id",
        "workflow_state",
        "next_recommended_action",
        "counts",
    },
)

COMPACT_WORKFLOW_COUNT_KEYS = frozenset(
    {
        "plan_drafts",
        "assets_total",
        "assets_approved",
        "assets_draft",
        "pending_review_assets",
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


def test_invariant_workflow_api_route_is_get_only() -> None:
    module_source = inspect.getsource(marketing_campaign_routes)
    assert '@router.get("/{campaign_id}/workflow"' in module_source
    assert '@router.post("/{campaign_id}/workflow"' not in module_source
    assert '@router.patch("/{campaign_id}/workflow"' not in module_source
    assert '@router.put("/{campaign_id}/workflow"' not in module_source
    assert '@router.delete("/{campaign_id}/workflow"' not in module_source


def test_invariant_workflow_tool_registered_as_read_only() -> None:
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL.metadata.get("access_mode") == "read_only"
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL.metadata.get("execution_mode") == "read_only"
    assert is_real_read_only_executable(MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME)
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME not in WRITE_TOOL_NAMES
    assert not is_real_write_executable(MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME)


@pytest.mark.parametrize("agent_type", sorted(WORKFLOW_TOOL_ALLOWED, key=lambda t: t.value))
def test_invariant_workflow_tool_allowed_for_planner_types(agent_type: AgentType) -> None:
    names = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME in names


@pytest.mark.parametrize("agent_type", sorted(WORKFLOW_TOOL_DENIED, key=lambda t: t.value))
def test_invariant_workflow_tool_denied_for_copywriter_researcher_critic(
    agent_type: AgentType,
) -> None:
    names = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME not in names


def test_invariant_compact_workflow_tool_output_shape() -> None:
    workflow = CampaignWorkflowResponse(
        campaign_id=uuid4(),
        workflow_state=CampaignWorkflowState.PLAN_READY,
        counts=CampaignWorkflowCounts(
            plan_drafts=1,
            assets_total=0,
            assets_approved=0,
            assets_draft=0,
        ),
        next_recommended_action="generate_assets",
    )
    payload = format_marketing_campaign_workflow_compact(workflow)
    assert set(payload.keys()) == COMPACT_WORKFLOW_OUTPUT_KEYS
    assert set(payload["counts"].keys()) == COMPACT_WORKFLOW_COUNT_KEYS
    blob = str(payload).lower()
    for marker in LEAK_MARKERS:
        if marker == "body":
            assert '"body"' not in blob
            assert "body_preview" not in blob
        else:
            assert marker not in blob


@pytest.mark.parametrize(
    "agent_type",
    [
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    ],
)
def test_invariant_prompt_templates_include_workflow_guidance(agent_type: AgentType) -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[agent_type]
    assert "marketing_campaign.workflow" in prompt
    assert _CAMPAIGN_WORKFLOW_GUIDANCE.split("\n")[0] in prompt
    lowered = prompt.lower()
    assert "never approve" in lowered
    assert "schedule" in lowered


def test_invariant_copywriter_prompt_excludes_workflow_tool_guidance() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.COPYWRITER]
    assert "marketing_campaign.workflow" not in prompt


def test_invariant_generate_assets_bulk_write_tool_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in PHASE_13_FORBIDDEN_AGENT_TOOLS:
        assert forbidden not in registered
    assert "campaign_plan_draft.generate_assets" in registered
    assert is_real_write_executable("campaign_plan_draft.generate_assets") is False
    for forbidden in ("content_asset.approve", "content_asset.publish"):
        assert forbidden in FORBIDDEN_AGENT_TOOL_NAMES


def test_invariant_domain_compute_is_pure_no_db_writes() -> None:
    compute_source = inspect.getsource(campaign_workflow_domain.compute_campaign_workflow)
    lowered = compute_source.lower()
    assert "session" not in lowered
    assert "commit" not in lowered
    assert "execute(" not in lowered
    assert "insert" not in lowered
    assert "update(" not in lowered


def test_invariant_workflow_service_has_no_mutations() -> None:
    service_source = inspect.getsource(campaign_workflow_service_module.CampaignWorkflowService)
    for forbidden in (".add(", ".commit(", ".delete(", ".flush(", "session.merge"):
        assert forbidden not in service_source
    assert "get_workflow" in service_source
    assert "compute_campaign_workflow" in service_source


def test_invariant_workflow_states_cover_lifecycle() -> None:
    values = {member.value for member in CampaignWorkflowState}
    assert values == {
        "planning",
        "plan_ready",
        "assets_generated",
        "content_in_revision",
        "ready_for_review",
        "approved_for_publication",
        "completed",
    }

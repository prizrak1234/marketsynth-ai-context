"""Phase AI.9.1 — marketing orchestrator scenario readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
import json
from uuid import uuid4

import pytest
from app.agents.scenario_context import (
    build_marketing_scenario_context,
    build_recommended_next_steps,
)
from app.agents.scenarios.contracts import MarketingScenarioType
from app.agents.scenarios.detector import _SCENARIO_PHRASES, detect_marketing_scenario
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.prompts.agent_chat_workflow import (
    _AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES,
    build_agent_chat_workflow_system_content,
)
from app.schemas.contracts import AgentType, CampaignWorkflowState
from app.services import agent_chat_service as agent_chat_service_module
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_REVISION_WRITE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    list_tools_for_agent_chat,
)
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import is_write_tool_visible_to_agent

ALL_SCENARIO_TYPES = frozenset(MarketingScenarioType)

SCENARIO_DETECTION_SAMPLES: dict[MarketingScenarioType, str] = {
    MarketingScenarioType.CONTENT_LAUNCH: "Создай план запуска контента",
    MarketingScenarioType.TELEGRAM_CONTENT_MONTH: "Создай контент-план на месяц для Telegram",
    MarketingScenarioType.LEAD_MAGNET: "Нужен лид-магнит для воронки",
    MarketingScenarioType.PRODUCT_ANNOUNCEMENT: "Запускаем новый продукт",
    MarketingScenarioType.CAMPAIGN_REVIVAL: "Давай оживим эту кампанию",
}

SCENARIO_CONTEXT_REQUIRED_KEYS = frozenset(
    {
        "scenario_type",
        "scenario_detected",
        "workflow_state",
        "next_recommended_action",
        "pending_review_assets",
        "recommended_next_steps",
    },
)

SCENARIO_LAYER_FORBIDDEN_AUTOMATION_MARKERS = (
    "content_asset.approve",
    "content_asset.publish",
    "content_asset.schedule",
    "publication_job.create",
    "publication_job.schedule",
    "auto-execute",
    "auto_execute",
)

ORCHESTRATOR_DATA_SOURCE_MARKERS = (
    "marketing_campaign.workflow",
    "marketing_campaign.overview",
    "review_queue.list",
    "publication_calendar.list",
)

AI_9_CHAT_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
    },
)


def test_invariant_all_scenario_types_have_detection_phrases() -> None:
    assert set(_SCENARIO_PHRASES.keys()) == set(ALL_SCENARIO_TYPES)


@pytest.mark.parametrize("scenario_type", sorted(ALL_SCENARIO_TYPES, key=lambda t: t.value))
def test_invariant_each_scenario_type_is_detectable(scenario_type: MarketingScenarioType) -> None:
    message = SCENARIO_DETECTION_SAMPLES[scenario_type]
    assert detect_marketing_scenario(message=message) == scenario_type


def test_invariant_unknown_scenario_uses_workflow_fallback_steps() -> None:
    assert detect_marketing_scenario(message="Что делать дальше?") is None
    context = build_marketing_scenario_context(
        scenario_type=None,
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
        next_recommended_action="human_review_required",
        pending_review_assets=3,
    )
    assert context["scenario_detected"] is False
    assert context["scenario_type"] is None
    steps = context["recommended_next_steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 2
    assert context["workflow_state"] == CampaignWorkflowState.READY_FOR_REVIEW.value
    joined = " ".join(steps).lower()
    assert "review" in joined


def test_invariant_scenario_context_always_has_workflow_state_and_steps() -> None:
    for scenario_type in (MarketingScenarioType.CONTENT_LAUNCH, None):
        context = build_marketing_scenario_context(
            scenario_type=scenario_type,
            workflow_state=CampaignWorkflowState.PLAN_READY.value,
            next_recommended_action="generate_assets",
            pending_review_assets=0,
        )
        assert set(context.keys()) == SCENARIO_CONTEXT_REQUIRED_KEYS
        assert context["workflow_state"] == CampaignWorkflowState.PLAN_READY.value
        assert isinstance(context["recommended_next_steps"], list)
        assert len(context["recommended_next_steps"]) >= 1


def test_invariant_scenario_layer_has_no_automation_tool_markers() -> None:
    context = build_marketing_scenario_context(
        scenario_type=MarketingScenarioType.CONTENT_LAUNCH,
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
        pending_review_assets=2,
    )
    encoded = json.dumps(context).lower()
    for marker in SCENARIO_LAYER_FORBIDDEN_AUTOMATION_MARKERS:
        assert marker not in encoded


def test_invariant_recommended_steps_do_not_claim_auto_execution() -> None:
    steps = build_recommended_next_steps(
        scenario_type=MarketingScenarioType.PRODUCT_ANNOUNCEMENT,
        workflow_state=CampaignWorkflowState.APPROVED_FOR_PUBLICATION.value,
    )
    joined = " ".join(steps).lower()
    assert "automatically" not in joined
    assert "auto-approve" not in joined
    assert "auto approve" not in joined


def test_invariant_orchestrator_prompt_includes_scenario_context_block() -> None:
    scenario_context = build_marketing_scenario_context(
        scenario_type=MarketingScenarioType.TELEGRAM_CONTENT_MONTH,
        workflow_state=CampaignWorkflowState.PLANNING.value,
    )
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.PLANNING.value,
        "next_recommended_action": "create_plan_draft",
        "pending_review_assets": 0,
        "scenario_context": scenario_context,
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Marketing scenario context" in content
    assert "recommended_next_steps" in content
    assert "workflow_state" in content
    assert CampaignWorkflowState.PLANNING.value in content


def test_invariant_orchestrator_coordinator_rules_when_scenario_detected() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
        "next_recommended_action": "human_review_required",
        "pending_review_assets": 1,
        "scenario_context": build_marketing_scenario_context(
            scenario_type=MarketingScenarioType.CONTENT_LAUNCH,
            workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
            pending_review_assets=1,
        ),
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Marketing orchestrator scenario mode" in content
    assert "Do not claim a step is done" in content
    for marker in ORCHESTRATOR_DATA_SOURCE_MARKERS:
        assert marker in _AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES


def test_invariant_orchestrator_rules_forbid_approve_schedule_publish_in_prompt() -> None:
    rules = _AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES.lower()
    assert "do not approve" in rules
    assert "schedule" in rules
    assert "publish" in rules


def test_invariant_copywriter_does_not_receive_scenario_context_block() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.PLANNING.value,
        "next_recommended_action": "create_plan_draft",
        "pending_review_assets": 0,
        "scenario_context": build_marketing_scenario_context(
            scenario_type=MarketingScenarioType.CONTENT_LAUNCH,
            workflow_state=CampaignWorkflowState.PLANNING.value,
        ),
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        revision_tools=True,
        agent_type=AgentType.COPYWRITER,
    )
    assert "Marketing scenario context" not in content


def test_invariant_ai9_added_no_new_tools() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden_name in (
        "marketing_scenario.detect",
        "marketing_scenario.run",
        "orchestrator.execute_plan",
        "campaign.execute",
    ):
        assert forbidden_name not in registered


def test_invariant_chat_tool_profile_unchanged_by_ai9() -> None:
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.ORCHESTRATOR) == []
    assert frozenset(
        {"content_asset.create_revision"},
    ) == AGENT_CHAT_REVISION_WRITE_TOOL_NAMES


def test_invariant_chat_profile_excludes_approve_schedule_publish() -> None:
    for forbidden in AI_9_CHAT_FORBIDDEN_TOOL_NAMES:
        assert forbidden not in AGENT_CHAT_TOOL_NAMES
    for name in ("content_asset.approve", "content_asset.publish"):
        assert name in FORBIDDEN_AGENT_TOOL_NAMES


def test_invariant_no_new_write_permissions_from_ai9() -> None:
    assert not is_write_tool_visible_to_agent(AgentType.ORCHESTRATOR, "content_asset.approve")
    assert not is_write_tool_visible_to_agent(AgentType.ORCHESTRATOR, "publication_job.create")
    assert not is_write_tool_visible_to_agent(AgentType.ORCHESTRATOR, "content_asset.publish")
    assert not is_write_tool_visible_to_agent(
        AgentType.ORCHESTRATOR,
        "campaign_plan_draft.create",
    )


def test_invariant_run_input_carries_scenario_context() -> None:
    scenario_context = build_marketing_scenario_context(
        scenario_type=None,
        workflow_state=CampaignWorkflowState.ASSETS_GENERATED.value,
    )
    payload = build_agent_chat_run_input_payload(
        prompt="What next?",
        project_id=uuid4(),
        workflow_context={
            "campaign_id": str(uuid4()),
            "workflow_state": CampaignWorkflowState.ASSETS_GENERATED.value,
            "next_recommended_action": "review_assets",
            "pending_review_assets": 0,
        },
        scenario_context=scenario_context,
    )
    assert payload["agent_chat"]["scenario_context"] == scenario_context


def test_invariant_agent_chat_service_builds_scenario_context() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    assert "build_marketing_scenario_context" in source
    assert "detect_marketing_scenario" in source
    assert "scenario_context" in source

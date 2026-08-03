"""Phase AI.9 — marketing orchestrator scenario detection and context."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.agents.scenario_context import build_marketing_scenario_context, build_recommended_next_steps
from app.agents.scenarios.contracts import MarketingScenarioType
from app.agents.scenarios.detector import detect_marketing_scenario
from app.prompts.agent_chat_workflow import (
    _AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES,
    build_agent_chat_workflow_system_content,
)
from app.schemas.contracts import AgentType, CampaignWorkflowState
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_chat_tool_settings import (
    AGENT_CHAT_REVISION_WRITE_TOOL_NAMES,
    AGENT_CHAT_TOOL_NAMES,
    list_tools_for_agent_chat,
)
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import is_write_tool_visible_to_agent


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Создай контент-план на месяц для Telegram", MarketingScenarioType.TELEGRAM_CONTENT_MONTH),
        ("We need a monthly content plan for telegram", MarketingScenarioType.TELEGRAM_CONTENT_MONTH),
        ("Запускаем новый продукт на следующей неделе", MarketingScenarioType.PRODUCT_ANNOUNCEMENT),
        ("Prepare a product launch announcement", MarketingScenarioType.PRODUCT_ANNOUNCEMENT),
        ("Нужен лид-магнит для воронки", MarketingScenarioType.LEAD_MAGNET),
        ("Create a lead magnet checklist", MarketingScenarioType.LEAD_MAGNET),
        ("Давай оживим эту кампанию", MarketingScenarioType.CAMPAIGN_REVIVAL),
        ("Revive this campaign with fresh posts", MarketingScenarioType.CAMPAIGN_REVIVAL),
        ("Создай план запуска контента", MarketingScenarioType.CONTENT_LAUNCH),
    ],
)
def test_detector_maps_phrases_to_scenarios(message: str, expected: MarketingScenarioType) -> None:
    assert detect_marketing_scenario(message=message) == expected


def test_detector_fallback_unknown_request() -> None:
    assert detect_marketing_scenario(message="Что делать дальше?") is None
    assert detect_marketing_scenario(message="Hello team") is None


def test_detector_workflow_hint_when_message_generic() -> None:
    detected = detect_marketing_scenario(
        message="",
        workflow_state=CampaignWorkflowState.COMPLETED.value,
    )
    assert detected == MarketingScenarioType.CAMPAIGN_REVIVAL


def test_scenario_context_includes_workflow_and_steps() -> None:
    context = build_marketing_scenario_context(
        scenario_type=MarketingScenarioType.TELEGRAM_CONTENT_MONTH,
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
        next_recommended_action="human_review_required",
        pending_review_assets=3,
    )
    assert context["scenario_type"] == MarketingScenarioType.TELEGRAM_CONTENT_MONTH.value
    assert context["scenario_detected"] is True
    assert context["workflow_state"] == CampaignWorkflowState.READY_FOR_REVIEW.value
    steps = context["recommended_next_steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 2
    assert any("Review Queue" in step for step in steps)


def test_scenario_context_fallback_steps_without_detected_scenario() -> None:
    context = build_marketing_scenario_context(
        scenario_type=None,
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
        pending_review_assets=2,
    )
    assert context["scenario_detected"] is False
    assert context["scenario_type"] is None
    assert len(context["recommended_next_steps"]) >= 2


def test_workflow_ready_for_review_steps_mention_review_and_schedule() -> None:
    steps = build_recommended_next_steps(
        scenario_type=None,
        workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
        pending_review_assets=3,
    )
    joined = " ".join(steps).lower()
    assert "review" in joined
    assert "approve" in joined
    assert "schedule" in joined


def test_orchestrator_prompt_includes_scenario_rules_when_detected() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
        "next_recommended_action": "human_review_required",
        "pending_review_assets": 3,
        "scenario_context": build_marketing_scenario_context(
            scenario_type=MarketingScenarioType.CONTENT_LAUNCH,
            workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
            pending_review_assets=3,
        ),
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert _AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES.splitlines()[0] in content
    assert "Marketing scenario context" in content
    assert "recommended_next_steps" in content
    assert "Do not claim a step is done" in content


def test_orchestrator_prompt_omits_coordinator_rules_when_scenario_not_detected() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": CampaignWorkflowState.READY_FOR_REVIEW.value,
        "next_recommended_action": "human_review_required",
        "pending_review_assets": 1,
        "scenario_context": build_marketing_scenario_context(
            scenario_type=None,
            workflow_state=CampaignWorkflowState.READY_FOR_REVIEW.value,
            pending_review_assets=1,
        ),
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Marketing orchestrator scenario mode" not in content
    assert "Marketing scenario context" in content


def test_strategist_prompt_does_not_include_scenario_block() -> None:
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
        agent_type=AgentType.STRATEGIST,
    )
    assert "Marketing scenario context" not in content


def test_ai9_added_no_new_write_tools() -> None:
    assert AGENT_CHAT_REVISION_WRITE_TOOL_NAMES == frozenset(
        {"content_asset.create_revision"},
    )
    forbidden_writes = frozenset(
        {
            "content_asset.approve",
            "content_asset.publish",
            "content_asset.schedule",
            "campaign_plan_draft.create",
            "campaign_plan_draft.generate_assets",
        },
    )
    for name in forbidden_writes:
        assert name not in AGENT_CHAT_TOOL_NAMES or name in {
            "campaign_plan_draft.create",
            "campaign_plan_draft.generate_assets",
        }
    assert not is_write_tool_visible_to_agent(
        AgentType.ORCHESTRATOR,
        "content_asset.approve",
    )


def test_chat_tool_registry_unchanged_no_scenario_write_tools() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    assert "marketing_scenario.run" not in registered
    assert "scenario.execute" not in registered
    assert list_tools_for_agent_chat(get_tool_registry(), AgentType.ORCHESTRATOR) == []


def test_run_input_carries_scenario_context() -> None:
    scenario_context = build_marketing_scenario_context(
        scenario_type=MarketingScenarioType.PRODUCT_ANNOUNCEMENT,
        workflow_state=CampaignWorkflowState.PLANNING.value,
    )
    payload = build_agent_chat_run_input_payload(
        prompt="Launch",
        project_id=uuid4(),
        workflow_context={
            "campaign_id": str(uuid4()),
            "workflow_state": CampaignWorkflowState.PLANNING.value,
            "next_recommended_action": "create_plan_draft",
            "pending_review_assets": 0,
        },
        scenario_context=scenario_context,
    )
    agent_chat = payload["agent_chat"]
    assert agent_chat["scenario_context"]["scenario_type"] == "product_announcement"
    encoded = json.dumps(agent_chat["scenario_context"])
    assert "plan_payload" not in encoded

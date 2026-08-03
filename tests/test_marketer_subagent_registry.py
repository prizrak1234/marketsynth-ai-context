"""Phase AI.10 — marketer sub-agent registry, router, and orchestrator persona routing."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.registry import (
    FORBIDDEN_PERSONA_TOOLS,
    get_subagent,
    get_subagent_prompt,
    list_subagents,
    validate_subagent_tool_allowlist,
)
from app.agents.marketer.router import detect_best_subagent
from app.core.config import get_settings
from app.prompts.agent_chat_workflow import build_agent_chat_workflow_system_content
from app.prompts.marketer_subagents import (
    ANALYST_PROMPT,
    COPYWRITER_PROMPT,
    RESEARCHER_PROMPT,
    STRATEGIST_PROMPT,
)
from app.schemas.contracts import AgentType
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.registry import get_tool_registry


@pytest.mark.parametrize("subagent_type", list(MarketerSubAgentType))
def test_registry_lists_all_four_subagents(subagent_type: MarketerSubAgentType) -> None:
    profiles = list_subagents()
    assert len(profiles) == 4
    types = {profile.subagent_type for profile in profiles}
    assert types == set(MarketerSubAgentType)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Перепиши пост для Telegram", MarketerSubAgentType.COPYWRITER),
        ("Перепиши этот пост", MarketerSubAgentType.COPYWRITER),
        ("Improve this post copy", MarketerSubAgentType.COPYWRITER),
        ("Проанализируй кампанию", MarketerSubAgentType.ANALYST),
        ("Analyze the campaign workflow", MarketerSubAgentType.ANALYST),
        ("Сделай контент-план на месяц", MarketerSubAgentType.STRATEGIST),
        ("Create a content plan for Q2", MarketerSubAgentType.STRATEGIST),
        ("Исследуй аудиторию для брифа", MarketerSubAgentType.RESEARCHER),
        ("Research the audience for this brief", MarketerSubAgentType.RESEARCHER),
    ],
)
def test_router_maps_phrases_to_subagents(
    message: str,
    expected: MarketerSubAgentType,
) -> None:
    assert detect_best_subagent(message=message) == expected


def test_router_unknown_falls_back_to_orchestrator() -> None:
    assert detect_best_subagent(message="Что делать дальше?") is None
    assert detect_best_subagent(message="Hello") is None


def test_subagent_prompts_match_registry() -> None:
    assert get_subagent_prompt(MarketerSubAgentType.STRATEGIST) == STRATEGIST_PROMPT
    assert get_subagent_prompt(MarketerSubAgentType.COPYWRITER) == COPYWRITER_PROMPT
    assert get_subagent_prompt(MarketerSubAgentType.ANALYST) == ANALYST_PROMPT
    assert get_subagent_prompt(MarketerSubAgentType.RESEARCHER) == RESEARCHER_PROMPT


def test_personas_exclude_forbidden_tools() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for profile in list_subagents():
        validate_subagent_tool_allowlist(profile)
        assert not (profile.allowed_tools & FORBIDDEN_PERSONA_TOOLS)
        assert profile.allowed_tools <= registered


@pytest.fixture
def persona_write_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in (
        "AGENT_WRITE_TOOLS_ENABLED",
        "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
        "CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_persona_allowed_tools_within_mapped_agent_allowlist(
    persona_write_flags_on: None,
) -> None:
    for profile in list_subagents():
        agent_allowlist = get_agent_tool_allowlist(profile.mapped_agent_type)
        assert profile.allowed_tools <= agent_allowlist, profile.subagent_type


def test_orchestrator_prompt_includes_copywriter_persona() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": "assets_generated",
        "next_recommended_action": "review_assets",
        "pending_review_assets": 0,
        "subagent_routing": {"selected_subagent": "copywriter"},
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Copywriter persona" in content
    assert COPYWRITER_PROMPT.splitlines()[0] in content
    assert "selected_subagent" in content
    assert "content_asset.create_revision" in content


def test_orchestrator_without_subagent_routing_omits_persona_block() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": "planning",
        "next_recommended_action": "create_plan_draft",
        "pending_review_assets": 0,
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Marketer sub-agent routing" not in content
    assert "Copywriter persona" not in content


def test_strategist_agent_type_does_not_get_subagent_persona_overlay() -> None:
    workflow_context = {
        "campaign_id": str(uuid4()),
        "workflow_state": "planning",
        "next_recommended_action": "create_plan_draft",
        "pending_review_assets": 0,
        "subagent_routing": {"selected_subagent": "copywriter"},
    }
    content = build_agent_chat_workflow_system_content(
        workflow_context,
        agent_type=AgentType.STRATEGIST,
    )
    assert "Marketer sub-agent routing" not in content


def test_run_input_carries_subagent_routing() -> None:
    payload = build_agent_chat_run_input_payload(
        prompt="Перепиши пост",
        project_id=uuid4(),
        workflow_context={
            "campaign_id": str(uuid4()),
            "workflow_state": "assets_generated",
            "next_recommended_action": "review_assets",
            "pending_review_assets": 0,
        },
        subagent_routing={"selected_subagent": "copywriter"},
    )
    assert payload["agent_chat"]["subagent_routing"]["selected_subagent"] == "copywriter"


def test_copywriter_profile_metadata() -> None:
    profile = get_subagent(MarketerSubAgentType.COPYWRITER)
    assert profile.name == "Copywriter"
    assert "rewrite" in " ".join(profile.responsibilities).lower()
    assert "content_asset.get" in profile.allowed_tools

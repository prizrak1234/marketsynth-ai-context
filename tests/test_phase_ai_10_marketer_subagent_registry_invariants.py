"""Phase AI.10.1 — marketer sub-agent registry readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import uuid4

import pytest
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.registry import (
    FORBIDDEN_PERSONA_TOOLS,
    MarketerSubAgentProfile,
    get_subagent,
    get_subagent_prompt,
    list_subagents,
    validate_subagent_tool_allowlist,
)
from app.agents.marketer.router import _SUBAGENT_PHRASES, detect_best_subagent
from app.core.config import get_settings
from app.prompts import marketer_subagents as marketer_subagents_module
from app.prompts.agent_chat_workflow import build_agent_chat_workflow_system_content
from app.schemas.contracts import AgentType
from app.services import agent_chat_service as agent_chat_service_module
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.registry import get_tool_registry

ALL_SUBAGENT_TYPES = frozenset(MarketerSubAgentType)

ALLOWED_MAPPED_AGENT_TYPES = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.COPYWRITER,
        AgentType.ANALYST,
        AgentType.RESEARCHER,
    },
)

ROUTER_SAMPLES: dict[MarketerSubAgentType, str] = {
    MarketerSubAgentType.COPYWRITER: "Перепиши этот пост",
    MarketerSubAgentType.ANALYST: "Проанализируй кампанию",
    MarketerSubAgentType.STRATEGIST: "Сделай контент-план",
    MarketerSubAgentType.RESEARCHER: "Исследуй аудиторию",
}

PROFILE_FIELD_NAMES = frozenset(
    {
        "subagent_type",
        "name",
        "description",
        "responsibilities",
        "allowed_tools",
        "mapped_agent_type",
    },
)

MARKETER_FORBIDDEN_SOURCE_MARKERS = (
    "langgraph",
    "handoff_queue",
    "child_agent_run",
    "create_child_run",
    "subagent_memory",
    "parallel_execution",
)

EXECUTION_FORBIDDEN_REGISTRY_TOOLS = frozenset(
    {
        "marketer_subagent.run",
        "subagent.execute",
        "orchestrator.delegate",
    },
)


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


def test_invariant_exactly_four_subagents_registered() -> None:
    profiles = list_subagents()
    assert len(profiles) == 4
    assert {profile.subagent_type for profile in profiles} == set(ALL_SUBAGENT_TYPES)


def test_invariant_registry_covers_all_phrase_routes() -> None:
    assert set(_SUBAGENT_PHRASES.keys()) == set(ALL_SUBAGENT_TYPES)


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_each_profile_has_required_fields(subagent_type: MarketerSubAgentType) -> None:
    profile = get_subagent(subagent_type)
    assert set(MarketerSubAgentProfile.__dataclass_fields__) == PROFILE_FIELD_NAMES
    assert profile.name
    assert profile.description
    assert len(profile.responsibilities) >= 1
    assert len(profile.allowed_tools) >= 1


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_mapped_agent_type_is_allowed(subagent_type: MarketerSubAgentType) -> None:
    profile = get_subagent(subagent_type)
    assert profile.mapped_agent_type in ALLOWED_MAPPED_AGENT_TYPES


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_router_detects_each_subagent(subagent_type: MarketerSubAgentType) -> None:
    assert detect_best_subagent(message=ROUTER_SAMPLES[subagent_type]) == subagent_type


def test_invariant_unknown_message_no_selected_subagent() -> None:
    assert detect_best_subagent(message="Что делать дальше?") is None
    payload = build_agent_chat_run_input_payload(
        prompt="Что делать дальше?",
        project_id=uuid4(),
        workflow_context={
            "campaign_id": str(uuid4()),
            "workflow_state": "ready_for_review",
            "next_recommended_action": "human_review_required",
            "pending_review_assets": 1,
        },
    )
    assert "subagent_routing" not in payload.get("agent_chat", {})


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_prompt_exists_for_each_subagent(subagent_type: MarketerSubAgentType) -> None:
    prompt = get_subagent_prompt(subagent_type)
    assert isinstance(prompt, str)
    assert len(prompt.strip()) > 20


def test_invariant_all_four_prompt_constants_defined() -> None:
    for subagent_type in ALL_SUBAGENT_TYPES:
        assert subagent_type.value in marketer_subagents_module._SUBAGENT_PROMPTS


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_no_forbidden_approve_publish_schedule_tools(
    subagent_type: MarketerSubAgentType,
) -> None:
    profile = get_subagent(subagent_type)
    validate_subagent_tool_allowlist(profile)
    assert not (profile.allowed_tools & FORBIDDEN_PERSONA_TOOLS)


@pytest.mark.parametrize("subagent_type", sorted(ALL_SUBAGENT_TYPES, key=lambda t: t.value))
def test_invariant_allowed_tools_subset_of_mapped_agent_profile(
    persona_write_flags_on: None,
    subagent_type: MarketerSubAgentType,
) -> None:
    profile = get_subagent(subagent_type)
    assert profile.allowed_tools <= get_agent_tool_allowlist(profile.mapped_agent_type)


def test_invariant_persona_tools_exist_in_global_registry() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for profile in list_subagents():
        assert profile.allowed_tools <= registered


def test_invariant_orchestrator_receives_persona_overlay() -> None:
    content = build_agent_chat_workflow_system_content(
        {
            "campaign_id": str(uuid4()),
            "workflow_state": "assets_generated",
            "next_recommended_action": "review_assets",
            "pending_review_assets": 0,
            "subagent_routing": {"selected_subagent": "copywriter"},
        },
        agent_type=AgentType.ORCHESTRATOR,
    )
    assert "Marketer sub-agent routing" in content
    assert "Copywriter persona" in content


@pytest.mark.parametrize(
    "direct_agent_type",
    [AgentType.COPYWRITER, AgentType.STRATEGIST],
)
def test_invariant_direct_agent_types_no_persona_overlay(
    direct_agent_type: AgentType,
) -> None:
    content = build_agent_chat_workflow_system_content(
        {
            "campaign_id": str(uuid4()),
            "workflow_state": "planning",
            "next_recommended_action": "create_plan_draft",
            "pending_review_assets": 0,
            "subagent_routing": {"selected_subagent": "analyst"},
        },
        agent_type=direct_agent_type,
    )
    assert "Marketer sub-agent routing" not in content


def test_invariant_no_execution_tools_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for name in EXECUTION_FORBIDDEN_REGISTRY_TOOLS:
        assert name not in registered


def test_invariant_marketer_package_has_no_execution_imports() -> None:
    marketer_dir = Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer"
    combined = ""
    for path in marketer_dir.glob("*.py"):
        combined += path.read_text(encoding="utf-8") + "\n"
    for marker in MARKETER_FORBIDDEN_SOURCE_MARKERS:
        assert marker not in combined.lower()


def test_invariant_agent_chat_service_delegates_subagents_via_execution_layer() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    lowered = source.lower()
    assert "detect_best_subagent" in source
    assert "subagent_routing" in source
    assert "execute_subagent" in source
    assert "delegate_subagent" in source
    assert "_SUPPORTED_SUBAGENTS" in source
    assert "langgraph" not in lowered
    assert "handoff" not in lowered


def test_invariant_subagent_routing_only_when_detected() -> None:
    source = inspect.getsource(agent_chat_service_module.AgentChatService.send_message)
    assert "if selected_subagent is not None" in source

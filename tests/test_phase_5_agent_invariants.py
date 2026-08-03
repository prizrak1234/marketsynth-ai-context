"""Phase 5.8 — marketing agent role and permission invariants (freeze guard)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.agents.tool_matrix import (
    FORBIDDEN_AGENT_TOOL_NAMES,
    MARKETING_AGENT_TYPES,
    build_tool_matrix_api_payload,
    get_agent_tool_matrix,
)
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.mock_adapter import (
    MOCK_CONTENT_PLANNER_FINAL_CONTENT,
    MOCK_COPYWRITER_FINAL_CONTENT,
    MOCK_CRITIC_FINAL_CONTENT,
    MOCK_RESEARCHER_FINAL_CONTENT,
    MOCK_STRATEGIST_FINAL_CONTENT,
    MockLLMAdapter,
    _mock_content_planner_flow_tool_calls,
    _mock_copywriter_flow_tool_calls,
    _mock_critic_flow_tool_calls,
    _mock_orchestrator_flow_tool_calls,
    _mock_researcher_flow_tool_calls,
    _mock_strategy_flow_tool_calls,
)
from app.marketing.content_plan_quality import evaluate_content_plan_body
from app.marketing.copy_quality import evaluate_copy_draft_body
from app.marketing.orchestration import resolve_specialist_agent_type
from app.marketing.research_quality import evaluate_research_body
from app.marketing.review_quality import evaluate_review_body
from app.marketing.strategy_contracts import evaluate_strategy_draft_body
from app.marketing.workflow_smoke import create_orchestrator_run_payload
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import (
    CREATE_DRAFT_ALLOWED_AGENT_TYPES,
    content_asset_create_draft_enabled,
    is_agent_type_allowed_for_create_draft,
)
from fastapi.testclient import TestClient

SPECIALIST_CREATE_DRAFT_TYPES = [
    AgentType.STRATEGIST,
    AgentType.COPYWRITER,
    AgentType.CONTENT_PLANNER,
    AgentType.CRITIC,
    AgentType.RESEARCHER,
]

EXPECTED_READ_TOOLS: dict[AgentType, list[str]] = {
    AgentType.STRATEGIST: [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "search_brief",
        "task.get",
        "task.list_recent",
    ],
    AgentType.RESEARCHER: [
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "search_brief",
        "task.get",
        "task.list_recent",
    ],
    AgentType.COPYWRITER: [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_funnel.get",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "search_brief",
        "task.get",
    ],
    AgentType.CONTENT_PLANNER: [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "search_brief",
        "task.get",
    ],
    AgentType.CRITIC: [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "search_brief",
        "task.get",
    ],
    AgentType.ANALYST: [
        "campaign_asset.list",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "search_brief",
        "task.list_recent",
    ],
    AgentType.ORCHESTRATOR: [
        "campaign_asset.list",
        "content_asset.get",
        "content_asset.list",
        "marketing_brief.get",
        "marketing_brief.list",
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "marketing_funnel.gap_analysis",
        "marketing_funnel.get",
        "marketing_funnel.list",
        "marketing_funnel.step_assets",
        "memory.search",
        "project_context.get",
        "publication_calendar.list",
        "search_brief",
        "task.get",
        "task.list_recent",
    ],
}

FORBIDDEN_PROMPT_ID_PATTERNS = (
    "owner_id",
    "project_id",
    "task_id",
    "agent_run_id",
)


@pytest.fixture
def write_tools_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def write_tools_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("agent_type", SPECIALIST_CREATE_DRAFT_TYPES)
def test_specialist_create_draft_hidden_when_write_disabled(
    agent_type: AgentType,
    write_tools_off: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    matrix = get_agent_tool_matrix(get_settings())
    assert matrix[agent_type.value]["write"] == []


@pytest.mark.parametrize("agent_type", SPECIALIST_CREATE_DRAFT_TYPES)
def test_specialist_create_draft_visible_when_write_enabled(
    agent_type: AgentType,
    write_tools_on: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled()


def test_analyst_cannot_create_draft_even_when_write_enabled(write_tools_on: None) -> None:
    assert not is_agent_type_allowed_for_create_draft(AgentType.ANALYST)
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.ANALYST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert AgentType.ANALYST not in CREATE_DRAFT_ALLOWED_AGENT_TYPES


def test_no_agent_has_approve_publish_update_revision_tools() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in registered
    for agent_type in AgentType:
        allowlist = get_agent_tool_allowlist(agent_type)
        assert allowlist.isdisjoint(FORBIDDEN_AGENT_TOOL_NAMES)


def test_orchestrator_prompt_delegates_not_specialist_work() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.ORCHESTRATOR].lower()
    assert "delegate" in prompt
    assert "handoff" in prompt
    assert "do not create content assets via content_asset.create_draft" in prompt
    assert resolve_specialist_agent_type({"goal": "build content plan for launch"}) == (
        AgentType.CONTENT_PLANNER
    )


def test_orchestrator_mock_flow_skips_create_draft_tool() -> None:
    calls = _mock_orchestrator_flow_tool_calls(
        {"mock_orchestrator_flow": True, "funnel_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert calls is not None
    names = {call.name for call in calls}
    assert "project_context.get" in names
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in names


@pytest.mark.parametrize("agent_type", AgentType)
def test_tool_matrix_read_tools_match_expected(
    agent_type: AgentType,
    write_tools_off: None,
) -> None:
    expected = EXPECTED_READ_TOOLS[agent_type]
    actual = get_agent_tool_matrix(get_settings())[agent_type.value]["read"]
    assert actual == expected


def test_tool_matrix_api_payload_has_no_secret_keys(
    write_tools_off: None,
) -> None:
    payload = build_tool_matrix_api_payload(get_settings())
    blob = json.dumps(payload).lower()
    for token in ("api_key", "password", "secret", "bearer", "authorization"):
        assert token not in blob


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flow_key", "agent_value", "final_text", "flow_fn"),
    [
        (
            "mock_strategy_flow",
            "strategist",
            MOCK_STRATEGIST_FINAL_CONTENT,
            _mock_strategy_flow_tool_calls,
        ),
        (
            "mock_copywriter_flow",
            "copywriter",
            MOCK_COPYWRITER_FINAL_CONTENT,
            _mock_copywriter_flow_tool_calls,
        ),
        (
            "mock_content_planner_flow",
            "content_planner",
            MOCK_CONTENT_PLANNER_FINAL_CONTENT,
            _mock_content_planner_flow_tool_calls,
        ),
        (
            "mock_critic_flow",
            "critic",
            MOCK_CRITIC_FINAL_CONTENT,
            _mock_critic_flow_tool_calls,
        ),
        (
            "mock_researcher_flow",
            "researcher",
            MOCK_RESEARCHER_FINAL_CONTENT,
            _mock_researcher_flow_tool_calls,
        ),
    ],
)
async def test_specialist_mock_flows_use_tools_then_deterministic_final(
    flow_key: str,
    agent_value: str,
    final_text: str,
    flow_fn: object,
    write_tools_on: None,
) -> None:
    metadata = {flow_key: True, "agent_type": agent_value, "funnel_id": "f1"}
    round_one = flow_fn(metadata)  # type: ignore[operator]
    assert round_one is not None
    adapter = MockLLMAdapter()
    first = await adapter.generate(
        LLMGenerateInput(
            messages=[LLMMessage(role="user", content="go")],
            provider="mock",
            model="mock-model",
            metadata=metadata,
        ),
    )
    assert first.finish_reason == "tool_calls"
    second = await adapter.generate(
        LLMGenerateInput(
            messages=[
                LLMMessage(role="user", content="go"),
                LLMMessage(role="assistant", content=""),
                LLMMessage(role="tool", content="{}"),
            ],
            provider="mock",
            model="mock-model",
            metadata=metadata,
        ),
    )
    assert second.content == final_text


def test_quality_heuristics_do_not_raise_on_minimal_body() -> None:
    assert evaluate_strategy_draft_body("x").score < 1.0
    assert evaluate_copy_draft_body("email", "x").score < 1.0
    assert evaluate_content_plan_body("x").score < 1.0
    assert evaluate_review_body("x").score < 1.0
    assert evaluate_research_body("x").score < 1.0


def test_human_approve_is_http_only_not_agent_tool() -> None:
    tool_names = {tool.name for tool in get_tool_registry().list_registered()}
    assert "content_asset.approve" not in tool_names
    assert "content_asset.publish" not in tool_names
    for agent_type in AgentType:
        assert "approve" not in get_agent_tool_allowlist(agent_type)


def test_workflow_summary_response_has_no_secrets(
    client: TestClient,
    auth_headers: dict[str, str],
    write_tools_on: None,
) -> None:
    store = InMemoryGraphCheckpointStore()

    def _patch_runner():
        from app.graphs.runner import AgentGraphRunner as RealRunner

        class _RunnerWithStore(RealRunner):
            def __init__(self, *args, **kwargs):
                kwargs["checkpoint_store"] = store
                super().__init__(*args, **kwargs)

        return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)

    project_id = client.post(
        "/projects",
        json={"name": "Invariant summary"},
        headers=auth_headers,
    ).json()["id"]
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "B", "offer": "O"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "F", "brief_id": brief_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Step"},
        headers=auth_headers,
    )
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator"},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/agents/{orch['id']}",
        json={"config": {**orch.get("config", {}), "mock_orchestrator_flow": True}},
        headers=auth_headers,
    )
    client.post(
        "/agents",
        json={"project_id": project_id, "type": "content_planner"},
        headers=auth_headers,
    )
    parent = client.post(
        "/agent-runs",
        json={
            "agent_id": orch["id"],
            "input_payload": create_orchestrator_run_payload(
                brief_id=brief_id,
                funnel_id=funnel_id,
            ),
        },
        headers=auth_headers,
    ).json()
    with _patch_runner():
        client.post(
            f"/agent-runs/{parent['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    summary = client.get(
        f"/agent-runs/{parent['id']}/workflow-summary",
        headers=auth_headers,
    ).json()
    blob = json.dumps(summary).lower()
    for token in ("api_key", "password", "secret", "bearer", "authorization"):
        assert token not in blob


@pytest.mark.parametrize("agent_type", list(MARKETING_AGENT_TYPES))
def test_marketing_prompts_forbid_scope_ids_in_tool_args(agent_type: AgentType) -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[agent_type].lower()
    if agent_type == AgentType.STRATEGIST:
        assert "do not ask for or include owner_id" in prompt
        assert "project_id" in prompt
        assert "agent_run_id" in prompt
    else:
        assert "do not pass owner_id" in prompt
        for pattern in FORBIDDEN_PROMPT_ID_PATTERNS:
            assert pattern in prompt


def test_marketing_agent_types_frozen_in_matrix() -> None:
    matrix_keys = set(get_agent_tool_matrix().keys())
    for agent_type in MARKETING_AGENT_TYPES:
        assert agent_type.value in matrix_keys


def test_phase_3_invariants_suite_present() -> None:
    """Regression guard: Phase 3 freeze tests must remain in the repository."""
    path = Path(__file__).parent / "test_phase_3_invariants.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tests = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert len(tests) >= 12
    assert "test_succeeded_agent_run_cannot_execute_again" in tests


def test_tool_matrix_endpoint_requires_auth(client: TestClient) -> None:
    assert client.get("/agents/tool-matrix").status_code in (401, 403)


def test_tool_matrix_endpoint_returns_matrix(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/agents/tool-matrix", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "agents" in body
    strategist = next(row for row in body["agents"] if row["agent_type"] == "strategist")
    assert strategist["read_tools"] == EXPECTED_READ_TOOLS[AgentType.STRATEGIST]
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in strategist["read_tools"]

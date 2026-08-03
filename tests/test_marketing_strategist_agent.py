"""Phase 5.0 — marketing strategist agent MVP."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.funnel_contracts import FunnelStepType
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.marketing_funnel_service import MarketingFunnelService
from app.services.projects_service import ProjectService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import content_asset_create_draft_enabled
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.researcher_tool_names import (
    RESEARCHER_READ_ONLY_TOOL_COUNT,
    RESEARCHER_READ_ONLY_TOOL_NAMES,
)

STRATEGIST_CAPABILITY_NAMES = [
    "read_project_context",
    "read_marketing_briefs",
    "read_content_assets",
    "read_marketing_funnels",
    "analyze_funnel_gaps",
    "create_strategy_draft",
]


@pytest.fixture
def enable_create_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(client: TestClient, enable_create_draft: None) -> TestClient:
    get_settings.cache_clear()
    return client


def _project_id(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Strategist Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _strategist_agent(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _seed_marketing_stack(
    db_session: AsyncSession,
    *,
    telegram_id: int,
) -> tuple[object, object, object, object, object]:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Strategist stack {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST),
    )
    assert agent is not None
    brief = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title="Launch brief",
        offer="Core offer",
    )
    assert brief is not None
    funnel = await MarketingFunnelService(db_session).create_funnel(
        owner.id,
        project.id,
        title="Launch funnel",
        brief_id=brief.id,
    )
    assert funnel is not None
    await MarketingFunnelService(db_session).create_step(
        owner.id,
        project.id,
        funnel.id,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    return owner, project, agent, brief, funnel


def test_strategist_template_contains_expected_capabilities() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.STRATEGIST]
    names = [cap.name for cap in template["capabilities"]]
    assert names == STRATEGIST_CAPABILITY_NAMES
    assert template["default_config"]["tools"]["profile"] == "strategist"
    assert template["default_config"]["llm"]["temperature"] == 0.3
    assert template["default_config"]["output"]["default_asset_type"] == "article"


def test_strategist_tool_profile_exposes_twelve_read_tools() -> None:
    allowlist = get_agent_tool_allowlist(AgentType.STRATEGIST)
    for name in RESEARCHER_READ_ONLY_TOOL_NAMES:
        assert name in allowlist
    strategist_tools = get_tool_registry().list_for_agent(AgentType.STRATEGIST)
    registry_names = {tool.name for tool in strategist_tools}
    assert len([name for name in registry_names if name in RESEARCHER_READ_ONLY_TOOL_NAMES]) == (
        RESEARCHER_READ_ONLY_TOOL_COUNT
    )


def test_write_tool_hidden_when_disabled() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.STRATEGIST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert content_asset_create_draft_enabled() is False


def test_write_tool_visible_when_both_flags_enabled(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.STRATEGIST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled() is True


def test_strategist_prompt_avoids_owner_project_injection() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.STRATEGIST]
    lowered = prompt.lower()
    assert "owner_id" in lowered
    assert "do not ask" in lowered or "never" in lowered or "do not" in lowered
    assert "project_id" in lowered
    assert "approve" in lowered


def test_strategist_prompt_builder_includes_run_context_ids() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.STRATEGIST,
            agent_config={},
            input_payload={
                "goal": "analyze funnel and create strategy draft",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert "analyze funnel" in user_message.content


def test_strategist_dry_run_read_only_succeeds(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    agent = _strategist_agent(client, auth_headers, project_id)
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"prompt": "Review strategy", "goal": "read-only review"},
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["output_payload"]["content"] == "Mock LLM response"


def test_strategist_run_can_call_funnel_gap_analysis(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Gap Strategist")
    agent = _strategist_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Gap funnel"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "funnel_id": funnel_id,
                "goal": "gap analysis",
                "force_tool_call": "marketing_funnel.gap_analysis",
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"]["tool_names"] == ["marketing_funnel.gap_analysis"]
    assert body["output_payload"]["content"] == "Mock strategist final answer after tools"


def test_strategist_mock_strategy_flow_executes_gap_and_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Mock flow")
    agent = _strategist_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Strategy funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_strategy_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "funnel_id": funnel_id,
                "goal": "analyze funnel and create strategy draft",
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert set(body["output_payload"]["tools"]["tool_names"]) == {
        "marketing_funnel.gap_analysis",
        "content_asset.create_draft",
    }
    assert body["output_payload"]["content"] == "Mock strategist final answer after tools"


@pytest.mark.asyncio
async def test_strategist_create_draft_asset_is_draft_with_run_context(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief, funnel = await _seed_marketing_stack(
        db_session,
        telegram_id=9801,
    )
    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={
            "funnel_id": str(funnel.id),
            "brief_id": str(brief.id),
            "mock_tool_call": {
                "id": "call_strat_draft",
                "type": "function",
                "function": {
                    "name": "content_asset.create_draft",
                    "arguments": {
                        "brief_id": str(brief.id),
                        "type": "article",
                        "title": "Marketing Strategy Draft",
                        "body": (
                            "## Summary\nStrategy body\n\n"
                            "## Funnel gaps\nGaps\n\n"
                            "## Recommended assets\nAssets\n\n"
                            "## Next actions\nActions\n\n"
                            "## Risks\nRisks"
                        ),
                    },
                },
            },
        },
        metadata={},
    )
    assert run is not None

    from app.executors.agent_run_executor import AgentRunExecutor
    from app.services.llm_requests import LLMRequestService

    executor = AgentRunExecutor(
        db_session,
        run_service,
        LLMRequestService(db_session),
    )
    completed = await executor.execute_run(run.id, owner.id)
    await db_session.commit()
    assert completed.status.value == "succeeded"

    assets = await ContentAssetRepository(db_session).list_by_project(
        owner.id,
        project.id,
    )
    strategy_assets = [row for row in assets if row.title == "Marketing Strategy Draft"]
    assert len(strategy_assets) == 1
    asset = strategy_assets[0]
    assert asset.status.value == "draft"
    assert asset.agent_run_id == run.id


def test_strategist_cannot_approve_via_tools() -> None:
    tools = {tool.name for tool in get_tool_registry().list_registered()}
    assert "content_asset.approve" not in tools
    assert "marketing_brief.approve" not in tools


def test_analyst_profile_still_cannot_use_create_draft(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.ANALYST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools


def test_langgraph_strategist_run_with_gap_analysis(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Graph strategist")
    agent = _strategist_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Graph funnel"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "funnel_id": funnel_id,
                "mock_tool_call": {
                    "id": "call_graph_gap",
                    "type": "function",
                    "function": {
                        "name": "marketing_funnel.gap_analysis",
                        "arguments": {"funnel_id": funnel_id},
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"]["tool_names"] == ["marketing_funnel.gap_analysis"]


def test_audit_logs_strategist_tool_calls(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Audit strategist")
    agent = _strategist_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Audit funnel"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "funnel_id": funnel_id,
                "force_tool_call": "marketing_funnel.gap_analysis",
            },
        },
        headers=auth_headers,
    ).json()

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "marketing_funnel.gap_analysis"
    assert logs[0]["status"] == "succeeded"


def test_output_payload_tools_counts_read_and_write(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Tools summary")
    agent = _strategist_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Summary funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_strategy_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"funnel_id": funnel_id},
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    tools_summary = response.json()["output_payload"]["tools"]
    assert tools_summary["executed_count"] == 2
    assert tools_summary["failed_count"] == 0
    assert set(tools_summary["tool_names"]) == {
        "marketing_funnel.gap_analysis",
        "content_asset.create_draft",
    }

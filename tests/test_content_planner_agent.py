"""Phase 5.3 — content planner agent MVP."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.content_plan_quality import (
    CONTENT_PLAN_PURPOSE,
    build_mock_content_plan_body,
    default_content_planner_draft_metadata,
)
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
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import content_asset_create_draft_enabled
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

PLANNER_CAPABILITY_NAMES = [
    "read_marketing_briefs",
    "read_content_assets",
    "read_marketing_funnels",
    "analyze_funnel_gaps",
    "create_content_plan_draft",
]

PLANNER_READ_TOOL_NAMES = [
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
    "task.get",
]

COPYWRITER_CAPABILITY_NAMES = [
    "read_marketing_briefs",
    "read_content_assets",
    "read_funnel_context",
    "create_copy_draft",
]

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
    name: str = "Planner Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _planner_agent(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "content_planner"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _seed_planner_stack(
    db_session: AsyncSession,
    *,
    telegram_id: int,
) -> tuple[object, object, object, object, object]:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Planner stack {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.CONTENT_PLANNER),
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


def test_content_planner_template_contains_expected_capabilities() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.CONTENT_PLANNER]
    names = [cap.name for cap in template["capabilities"]]
    assert names == PLANNER_CAPABILITY_NAMES
    assert template["default_config"]["tools"]["profile"] == "content_planner"
    assert template["default_config"]["llm"]["temperature"] == 0.4
    assert template["default_config"]["output"]["default_asset_type"] == "article"
    assert template["default_config"]["output"]["default_asset_title"] == "Content Plan Draft"


def test_content_planner_tool_profile_includes_gap_analysis() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.CONTENT_PLANNER)
    names = [tool.name for tool in tools]
    assert names == PLANNER_READ_TOOL_NAMES
    assert "marketing_funnel.gap_analysis" in names


def test_write_tool_hidden_when_disabled() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.CONTENT_PLANNER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert content_asset_create_draft_enabled() is False


def test_write_tool_visible_when_both_flags_enabled(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.CONTENT_PLANNER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled() is True


def test_content_planner_prompt_forbids_approve_publish_linking() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.CONTENT_PLANNER]
    lowered = prompt.lower()
    assert "approve" in lowered
    assert "publish" in lowered
    assert "link" in lowered
    assert "owner_id" in lowered
    assert "project_id" in lowered


def test_content_planner_prompt_builder_includes_run_context_ids() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.CONTENT_PLANNER,
            agent_config={},
            input_payload={
                "goal": "plan content for launch funnel",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert "plan content for launch funnel" in user_message.content


def test_mock_content_planner_flow_creates_draft_when_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Mock planner flow")
    agent = _planner_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Planner funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_content_planner_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "funnel_id": funnel_id,
                "goal": "plan content for launch funnel",
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
    assert body["output_payload"]["content"] == "Mock content planner final answer after tools"


@pytest.mark.asyncio
async def test_content_planner_create_draft_is_draft_with_metadata(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief, funnel = await _seed_planner_stack(
        db_session,
        telegram_id=9820,
    )
    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    body = build_mock_content_plan_body(goal="Launch plan")
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={
            "funnel_id": str(funnel.id),
            "brief_id": str(brief.id),
            "mock_tool_call": {
                "id": "call_plan_draft",
                "type": "function",
                "function": {
                    "name": "content_asset.create_draft",
                    "arguments": {
                        "brief_id": str(brief.id),
                        "type": "article",
                        "title": "Content Plan Draft",
                        "body": body,
                        "metadata": default_content_planner_draft_metadata(
                            funnel_id=str(funnel.id),
                            goal="Launch plan",
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
    plan_assets = [row for row in assets if row.title == "Content Plan Draft"]
    assert len(plan_assets) == 1
    asset = plan_assets[0]
    assert asset.status.value == "draft"
    meta = asset.asset_metadata or {}
    assert meta.get("purpose") == CONTENT_PLAN_PURPOSE
    assert meta.get("source") == "content_planner_agent"
    assert "quality" in meta
    assert meta["quality"]["score"] >= 0.8


def test_langgraph_content_planner_run_with_mock_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Graph planner")
    agent = _planner_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Graph funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_content_planner_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"funnel_id": funnel_id, "goal": "plan"},
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
    assert "marketing_funnel.gap_analysis" in body["output_payload"]["tools"]["tool_names"]
    assert "content_asset.create_draft" in body["output_payload"]["tools"]["tool_names"]


def test_audit_logs_planner_gap_and_create_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Audit planner")
    agent = _planner_agent(client, auth_headers, project_id)
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Audit funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_content_planner_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"funnel_id": funnel_id, "goal": "audit plan"},
        },
        headers=auth_headers,
    ).json()

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    tool_names = {row["tool_name"] for row in logs}
    assert tool_names == {
        "marketing_funnel.gap_analysis",
        "content_asset.create_draft",
    }
    assert all(row["status"] == "succeeded" for row in logs)


def test_strategist_and_copywriter_templates_unchanged() -> None:
    strategist = DEFAULT_AGENT_TEMPLATES[AgentType.STRATEGIST]
    copywriter = DEFAULT_AGENT_TEMPLATES[AgentType.COPYWRITER]
    assert [cap.name for cap in strategist["capabilities"]] == STRATEGIST_CAPABILITY_NAMES
    assert [cap.name for cap in copywriter["capabilities"]] == COPYWRITER_CAPABILITY_NAMES
    assert strategist["default_config"]["output"]["default_asset_title"] == (
        "Marketing Strategy Draft"
    )
    assert copywriter["default_config"]["output"]["default_asset_type"] == "email"


@pytest.mark.asyncio
async def test_low_quality_content_plan_does_not_block_creation(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, _brief, _funnel = await _seed_planner_stack(
        db_session,
        telegram_id=9821,
    )
    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={},
        metadata={},
    )
    assert run is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_thin_plan",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "article",
                "title": "Thin Plan",
                "body": "Too short",
                "metadata": default_content_planner_draft_metadata(goal="x"),
            },
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.CONTENT_PLANNER,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    thin = next(row for row in assets if row.title == "Thin Plan")
    assert thin.asset_metadata["quality"]["score"] < 1.0

"""Phase 5.5 — researcher agent MVP."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.research_quality import (
    RESEARCH_DRAFT_PURPOSE,
    build_mock_research_body,
    default_researcher_draft_metadata,
)
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.projects_service import ProjectService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import content_asset_create_draft_enabled
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.researcher_tool_names import (
    RESEARCHER_READ_ONLY_TOOL_COUNT,
    RESEARCHER_READ_ONLY_TOOL_NAMES,
)

RESEARCHER_CAPABILITY_NAMES = [
    "read_project_context",
    "read_memory",
    "read_marketing_briefs",
    "read_content_assets",
    "read_marketing_funnels",
    "create_research_draft",
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
    name: str = "Researcher Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _researcher_agent(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _seed_researcher_stack(
    db_session: AsyncSession,
    *,
    telegram_id: int,
) -> tuple[object, object, object, object]:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Researcher stack {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.RESEARCHER),
    )
    assert agent is not None
    brief = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title="Research brief",
        offer="Core offer",
    )
    assert brief is not None
    return owner, project, agent, brief


def test_researcher_template_contains_expected_capabilities() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.RESEARCHER]
    names = [cap.name for cap in template["capabilities"]]
    assert names == RESEARCHER_CAPABILITY_NAMES
    assert template["default_config"]["tools"]["profile"] == "researcher"
    assert template["default_config"]["llm"]["temperature"] == 0.25
    assert template["default_config"]["output"]["default_asset_title"] == "Research Draft"


def test_researcher_tool_profile_has_twelve_read_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    names = [tool.name for tool in tools]
    assert names == RESEARCHER_READ_ONLY_TOOL_NAMES
    assert len(names) == RESEARCHER_READ_ONLY_TOOL_COUNT


def test_write_tool_hidden_when_disabled() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.RESEARCHER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert content_asset_create_draft_enabled() is False


def test_write_tool_visible_when_both_flags_enabled(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.RESEARCHER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled() is True


def test_researcher_prompt_requires_assumptions_and_external_validation() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.RESEARCHER]
    lowered = prompt.lower()
    assert "assumption" in lowered
    assert "external validation" in lowered
    assert "web" in lowered
    assert "approve" in lowered
    assert "publish" in lowered


def test_researcher_prompt_builder_includes_run_context_ids() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            agent_config={},
            input_payload={
                "goal": "prepare internal research memo",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "research_topic": "audience objections",
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert "audience objections" in user_message.content
    assert "prepare internal research memo" in user_message.content


def test_mock_researcher_flow_creates_draft_and_calls_memory(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Mock researcher flow")
    agent = _researcher_agent(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief", "offer": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Funnel"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_researcher_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "research_topic": "audience objections",
                "goal": "prepare internal research memo",
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert set(body["output_payload"]["tools"]["tool_names"]) == {
        "marketing_brief.get",
        "marketing_funnel.gap_analysis",
        "memory.search",
        "content_asset.create_draft",
    }
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"


@pytest.mark.asyncio
async def test_research_draft_metadata_and_status(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief = await _seed_researcher_stack(
        db_session,
        telegram_id=9840,
    )
    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    body = build_mock_research_body(
        goal="memo",
        research_topic="audience objections",
    )
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={
            "brief_id": str(brief.id),
            "mock_tool_call": {
                "id": "call_research_draft",
                "type": "function",
                "function": {
                    "name": "content_asset.create_draft",
                    "arguments": {
                        "brief_id": str(brief.id),
                        "type": "article",
                        "title": "Research Draft",
                        "body": body,
                        "metadata": default_researcher_draft_metadata(
                            research_topic="audience objections",
                            goal="memo",
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
    research_assets = [row for row in assets if row.title == "Research Draft"]
    assert len(research_assets) == 1
    asset = research_assets[0]
    assert asset.status.value == "draft"
    meta = asset.asset_metadata or {}
    assert meta.get("purpose") == RESEARCH_DRAFT_PURPOSE
    assert meta.get("source") == "researcher_agent"
    assert meta.get("research_topic") == "audience objections"
    assert "quality" in meta
    assert meta["quality"]["score"] >= 0.8


def test_researcher_cannot_approve_publish_or_update_via_tools() -> None:
    tools = {tool.name for tool in get_tool_registry().list_registered()}
    assert "content_asset.approve" not in tools
    assert not any(name.startswith("content_asset.") and "approve" in name for name in tools)
    assert not any("publish" in name for name in tools)
    assert not any("revision" in name for name in tools)


def test_langgraph_researcher_run_with_mock_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Graph researcher")
    agent = _researcher_agent(client, auth_headers, project_id)
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_researcher_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "research_topic": "competitors",
                "goal": "research",
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
    tool_names = body["output_payload"]["tools"]["tool_names"]
    assert "memory.search" in tool_names
    assert "content_asset.create_draft" in tool_names


def test_audit_logs_researcher_read_and_create_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Audit researcher")
    agent = _researcher_agent(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief", "offer": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_researcher_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "brief_id": brief_id,
                "research_topic": "market",
                "goal": "audit",
            },
        },
        headers=auth_headers,
    ).json()

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    tool_names = {row["tool_name"] for row in logs}
    assert "marketing_brief.get" in tool_names
    assert "memory.search" in tool_names
    assert "content_asset.create_draft" in tool_names


def test_strategist_template_unchanged() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.STRATEGIST]
    names = [cap.name for cap in template["capabilities"]]
    assert names == STRATEGIST_CAPABILITY_NAMES


@pytest.mark.asyncio
async def test_low_quality_research_draft_does_not_block_creation(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, _brief = await _seed_researcher_stack(
        db_session,
        telegram_id=9841,
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
            id="call_thin_research",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "article",
                "title": "Thin Research",
                "body": "Too short",
                "metadata": default_researcher_draft_metadata(goal="x"),
            },
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.RESEARCHER,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    thin = next(row for row in assets if row.title == "Thin Research")
    assert thin.asset_metadata["quality"]["score"] < 1.0

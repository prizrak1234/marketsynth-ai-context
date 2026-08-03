"""Phase 5.4 — critic agent MVP."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.review_quality import (
    CONTENT_REVIEW_PURPOSE,
    build_mock_review_body,
    default_critic_draft_metadata,
)
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.projects_service import ProjectService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import content_asset_create_draft_enabled
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

CRITIC_CAPABILITY_NAMES = [
    "read_marketing_briefs",
    "read_content_assets",
    "read_marketing_funnels",
    "review_content_quality",
    "create_review_draft",
]

CRITIC_READ_TOOL_NAMES = [
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
    name: str = "Critic Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _critic_agent(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "critic"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _seed_critic_stack(
    db_session: AsyncSession,
    *,
    telegram_id: int,
) -> tuple[object, object, object, object, object]:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Critic stack {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.CRITIC),
    )
    assert agent is not None
    brief = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title="Launch brief",
        offer="Core offer",
    )
    assert brief is not None
    source = await ContentAssetService(db_session).create(
        owner.id,
        project.id,
        asset_type="email",
        title="Launch Email",
        body="Subject line: Hello\n\nBody: Offer text\n\nCTA: Buy now",
        brief_id=brief.id,
    )
    assert source is not None
    return owner, project, agent, brief, source


def test_critic_template_contains_expected_capabilities() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.CRITIC]
    names = [cap.name for cap in template["capabilities"]]
    assert names == CRITIC_CAPABILITY_NAMES
    assert template["default_config"]["tools"]["profile"] == "critic"
    assert template["default_config"]["llm"]["temperature"] == 0.2
    assert template["default_config"]["output"]["default_asset_title"] == "Content Review Draft"


def test_critic_tool_profile_includes_gap_analysis() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.CRITIC)
    names = [tool.name for tool in tools]
    assert names == CRITIC_READ_TOOL_NAMES
    assert "marketing_funnel.gap_analysis" in names


def test_write_tool_hidden_when_disabled() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.CRITIC)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert content_asset_create_draft_enabled() is False


def test_write_tool_visible_when_both_flags_enabled(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.CRITIC)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled() is True


def test_critic_prompt_forbids_approve_publish_edit_source() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.CRITIC]
    lowered = prompt.lower()
    assert "approve" in lowered
    assert "publish" in lowered
    assert "modify" in lowered or "never" in lowered
    assert "source" in lowered
    assert "owner_id" in lowered


def test_critic_prompt_builder_includes_run_context_ids() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    source_asset_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.CRITIC,
            agent_config={},
            input_payload={
                "goal": "review this copy before approval",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "source_asset_id": source_asset_id,
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert source_asset_id in user_message.content
    assert "review this copy" in user_message.content


def test_mock_critic_flow_creates_review_draft_when_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Mock critic flow")
    agent = _critic_agent(client, auth_headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief", "offer": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    source_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "Source Email",
            "body": "Subject: Hi\n\nCTA: Go",
        },
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_critic_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "brief_id": brief_id,
                "source_asset_id": source_id,
                "goal": "review this copy before approval",
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert set(body["output_payload"]["tools"]["tool_names"]) == {
        "content_asset.get",
        "marketing_brief.get",
        "content_asset.create_draft",
    }
    assert body["output_payload"]["content"] == "Mock critic final answer after tools"


@pytest.mark.asyncio
async def test_review_draft_metadata_and_source_unchanged(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief, source = await _seed_critic_stack(
        db_session,
        telegram_id=9830,
    )
    source_before = await ContentAssetRepository(db_session).get_by_id_for_owner(
        source.id,
        owner.id,
        project.id,
    )
    assert source_before is not None
    before_title = source_before.title
    before_body = source_before.body
    before_version = source_before.current_version_number

    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    body = build_mock_review_body(goal="Review launch email")
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={
            "source_asset_id": str(source.id),
            "mock_tool_call": {
                "id": "call_review_draft",
                "type": "function",
                "function": {
                    "name": "content_asset.create_draft",
                    "arguments": {
                        "brief_id": str(brief.id),
                        "type": "article",
                        "title": "Content Review Draft",
                        "body": body,
                        "metadata": default_critic_draft_metadata(
                            source_asset_id=str(source.id),
                            goal="Review launch email",
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

    source_after = await ContentAssetRepository(db_session).get_by_id_for_owner(
        source.id,
        owner.id,
        project.id,
    )
    assert source_after is not None
    assert source_after.title == before_title
    assert source_after.body == before_body
    assert source_after.current_version_number == before_version

    assets = await ContentAssetRepository(db_session).list_by_project(
        owner.id,
        project.id,
    )
    reviews = [row for row in assets if row.title == "Content Review Draft"]
    assert len(reviews) == 1
    review = reviews[0]
    assert review.status.value == "draft"
    meta = review.asset_metadata or {}
    assert meta.get("purpose") == CONTENT_REVIEW_PURPOSE
    assert meta.get("source") == "critic_agent"
    assert meta.get("source_asset_id") == str(source.id)
    assert "quality" in meta
    assert meta["quality"]["score"] >= 0.8


def test_critic_cannot_approve_via_tools() -> None:
    tools = {tool.name for tool in get_tool_registry().list_registered()}
    assert "content_asset.approve" not in tools


def test_langgraph_critic_run_with_mock_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Graph critic")
    agent = _critic_agent(client, auth_headers, project_id)
    source_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Graph source", "body": "Copy"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_critic_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "source_asset_id": source_id,
                "goal": "review",
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
    assert "content_asset.get" in body["output_payload"]["tools"]["tool_names"]
    assert "content_asset.create_draft" in body["output_payload"]["tools"]["tool_names"]


def test_audit_logs_critic_get_and_create_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Audit critic")
    agent = _critic_agent(client, auth_headers, project_id)
    source_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Audit source", "body": "Text"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_critic_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "source_asset_id": source_id,
                "goal": "audit review",
            },
        },
        headers=auth_headers,
    ).json()

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    tool_names = {row["tool_name"] for row in logs}
    assert "content_asset.get" in tool_names
    assert "content_asset.create_draft" in tool_names


def test_strategist_copywriter_planner_templates_unchanged() -> None:
    copywriter = DEFAULT_AGENT_TEMPLATES[AgentType.COPYWRITER]
    planner = DEFAULT_AGENT_TEMPLATES[AgentType.CONTENT_PLANNER]
    assert copywriter["default_config"]["output"]["default_asset_type"] == "email"
    assert planner["default_config"]["output"]["default_asset_title"] == "Content Plan Draft"


@pytest.mark.asyncio
async def test_low_quality_review_does_not_block_creation(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, _brief, source = await _seed_critic_stack(
        db_session,
        telegram_id=9831,
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
            id="call_thin_review",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "article",
                "title": "Thin Review",
                "body": "Too short",
                "metadata": default_critic_draft_metadata(
                    source_asset_id=str(source.id),
                    goal="x",
                ),
            },
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.CRITIC,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    thin = next(row for row in assets if row.title == "Thin Review")
    assert thin.asset_metadata["quality"]["score"] < 1.0

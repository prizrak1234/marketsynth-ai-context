"""Phase 5.2 — copywriter agent MVP."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.copy_quality import (
    COPY_DRAFT_PURPOSE,
    build_mock_copy_draft_body,
    default_copywriter_draft_metadata,
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

COPYWRITER_CAPABILITY_NAMES = [
    "read_marketing_briefs",
    "read_content_assets",
    "read_funnel_context",
    "create_copy_draft",
]

COPYWRITER_READ_TOOL_NAMES = [
    "campaign_asset.list",
    "content_asset.get",
    "content_asset.list",
    "marketing_brief.get",
    "marketing_brief.list",
    "marketing_funnel.get",
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
    name: str = "Copywriter Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _copywriter_agent(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
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
        ProjectCreate(owner_id=owner.id, name=f"Copywriter stack {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
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
    step = await MarketingFunnelService(db_session).create_step(
        owner.id,
        project.id,
        funnel.id,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    assert step is not None
    return owner, project, agent, brief, funnel


def test_copywriter_template_contains_expected_capabilities() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.COPYWRITER]
    names = [cap.name for cap in template["capabilities"]]
    assert names == COPYWRITER_CAPABILITY_NAMES
    assert template["default_config"]["tools"]["profile"] == "copywriter"
    assert template["default_config"]["llm"]["temperature"] == 0.5
    assert template["default_config"]["output"]["default_asset_type"] == "email"
    assert template["default_config"]["output"]["default_asset_title"] == "Copy Draft"


def test_copywriter_tool_profile_sees_only_allowed_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.COPYWRITER)
    names = [tool.name for tool in tools]
    assert names == COPYWRITER_READ_TOOL_NAMES
    assert "marketing_funnel.gap_analysis" not in names
    assert "marketing_funnel.list" not in names


def test_write_tool_hidden_when_disabled() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.COPYWRITER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools
    assert content_asset_create_draft_enabled() is False


def test_write_tool_visible_when_both_flags_enabled(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.COPYWRITER)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    assert content_asset_create_draft_enabled() is True


def test_copywriter_prompt_forbids_approve_publish_status() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.COPYWRITER]
    lowered = prompt.lower()
    assert "approve" in lowered
    assert "publish" in lowered
    assert "status" in lowered
    assert "owner_id" in lowered
    assert "project_id" in lowered


def test_copywriter_prompt_builder_includes_run_context_ids() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    step_id = str(uuid4())
    source_asset_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.COPYWRITER,
            agent_config={},
            input_payload={
                "goal": "write launch email",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "step_id": step_id,
                "source_asset_id": source_asset_id,
                "asset_type": "email",
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert step_id in user_message.content
    assert source_asset_id in user_message.content
    assert "email" in user_message.content


def test_copywriter_mock_flow_creates_draft_when_enabled(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Mock copy flow")
    agent = _copywriter_agent(client, auth_headers, project_id)
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
    step_id = client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Awareness"},
        headers=auth_headers,
    ).json()["id"]
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_copywriter_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "step_id": step_id,
                "asset_type": "email",
                "goal": "write launch email",
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
        "marketing_funnel.step_assets",
        "content_asset.create_draft",
    }
    assert body["output_payload"]["content"] == "Mock copywriter final answer after tools"


@pytest.mark.asyncio
async def test_copywriter_create_draft_asset_is_draft_with_run_context(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief, funnel = await _seed_marketing_stack(
        db_session,
        telegram_id=9810,
    )
    from app.services.agent_runs import AgentRunService

    run_service = AgentRunService(db_session)
    body = build_mock_copy_draft_body("email", goal="Launch")
    run = await run_service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={
            "brief_id": str(brief.id),
            "funnel_id": str(funnel.id),
            "mock_tool_call": {
                "id": "call_copy_draft",
                "type": "function",
                "function": {
                    "name": "content_asset.create_draft",
                    "arguments": {
                        "brief_id": str(brief.id),
                        "type": "email",
                        "title": "Copy Draft",
                        "body": body,
                        "metadata": default_copywriter_draft_metadata(goal="Launch"),
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
    copy_assets = [row for row in assets if row.title == "Copy Draft"]
    assert len(copy_assets) == 1
    asset = copy_assets[0]
    assert asset.status.value == "draft"
    assert asset.agent_run_id == run.id
    meta = asset.asset_metadata or {}
    assert meta.get("purpose") == COPY_DRAFT_PURPOSE
    assert meta.get("source") == "copywriter_agent"
    assert "quality" in meta
    assert meta["quality"]["score"] >= 0.0


def test_analyst_profile_still_cannot_use_create_draft(enable_create_draft: None) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.ANALYST)}
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME not in tools


def test_langgraph_copywriter_run_with_mock_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Graph copywriter")
    agent = _copywriter_agent(client, auth_headers, project_id)
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_copywriter_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"asset_type": "ad_copy", "goal": "ads"},
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
    assert "content_asset.create_draft" in body["output_payload"]["tools"]["tool_names"]


def test_audit_logs_copywriter_create_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = _project_id(client, auth_headers, "Audit copywriter")
    agent = _copywriter_agent(client, auth_headers, project_id)
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_copywriter_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"asset_type": "email", "goal": "audit"},
        },
        headers=auth_headers,
    ).json()

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    draft_logs = [row for row in logs if row["tool_name"] == "content_asset.create_draft"]
    assert len(draft_logs) == 1
    assert draft_logs[0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_low_quality_copy_draft_does_not_block_creation(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    owner, project, agent, brief, _funnel = await _seed_marketing_stack(
        db_session,
        telegram_id=9811,
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
            id="call_low_quality",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "email",
                "title": "Thin Copy",
                "body": "Too short",
                "metadata": default_copywriter_draft_metadata(goal="x"),
            },
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.COPYWRITER,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    thin = next(row for row in assets if row.title == "Thin Copy")
    assert thin.asset_metadata["quality"]["score"] < 1.0

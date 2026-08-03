"""Phase 4.9 — marketing funnel read-only tool execution tests."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetType
from app.marketing.funnel_contracts import FunnelStepAssetRole, FunnelStepType
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_funnel_service import MarketingFunnelService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.marketing_funnel_get import parse_marketing_funnel_get_arguments
from app.tools.funnel_tools import (
    MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
    MARKETING_FUNNEL_GET_TOOL_NAME,
    MARKETING_FUNNEL_LIST_TOOL_NAME,
    MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
    compute_funnel_gap_analysis,
)
from app.tools.openai_schema import tool_definition_to_openai_tool
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS
from app.tools.registry import (
    MARKETING_FUNNEL_GAP_ANALYSIS_TOOL,
    MARKETING_FUNNEL_GET_TOOL,
    MARKETING_FUNNEL_LIST_TOOL,
    MARKETING_FUNNEL_STEP_ASSETS_TOOL,
    get_tool_registry,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

EXPECTED_FUNNEL_TOOL_NAMES = [
    "marketing_funnel.gap_analysis",
    "marketing_funnel.get",
    "marketing_funnel.list",
    "marketing_funnel.step_assets",
]


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(
    *,
    owner_id,
    project_id,
    agent_id,
    agent_type: AgentType = AgentType.STRATEGIST,
    agent_run_id=None,
    request_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=agent_run_id or uuid4(),
        request_id=request_id or uuid4(),
    )


async def _seed_project_with_agent(
    db_session: AsyncSession,
    *,
    telegram_id: int,
    agent_type: AgentType = AgentType.STRATEGIST,
):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Funnel Tool Project {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=agent_type),
    )
    assert agent is not None
    return owner, project, agent


async def _seed_funnel(
    db_session: AsyncSession,
    owner,
    project,
    *,
    title: str = "Launch funnel",
) -> object:
    row = await MarketingFunnelService(db_session).create_funnel(
        owner.id,
        project.id,
        title=title,
    )
    assert row is not None
    return row


async def _seed_step(
    db_session: AsyncSession,
    owner,
    project,
    funnel,
    *,
    step_type: FunnelStepType,
    title: str,
) -> object:
    row = await MarketingFunnelService(db_session).create_step(
        owner.id,
        project.id,
        funnel.id,
        step_type=step_type,
        title=title,
    )
    assert row is not None
    return row


async def _seed_asset(
    db_session: AsyncSession,
    owner,
    project,
    *,
    title: str = "Asset",
    status: ContentAssetStatus = ContentAssetStatus.DRAFT,
) -> object:
    service = ContentAssetService(db_session)
    row = await service.create(
        owner.id,
        project.id,
        asset_type=ContentAssetType.LANDING_PAGE,
        title=title,
        body="Funnel asset body",
    )
    assert row is not None
    if status == ContentAssetStatus.APPROVED:
        approved = await service.approve_asset(owner.id, project.id, row.id)
        assert approved is not None
        return approved
    return row


def test_registry_exposes_four_funnel_read_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.STRATEGIST)
    names = [tool.name for tool in tools]
    for name in EXPECTED_FUNNEL_TOOL_NAMES:
        assert name in names


def test_openai_schemas_are_valid() -> None:
    for tool in (
        MARKETING_FUNNEL_GET_TOOL,
        MARKETING_FUNNEL_LIST_TOOL,
        MARKETING_FUNNEL_STEP_ASSETS_TOOL,
        MARKETING_FUNNEL_GAP_ANALYSIS_TOOL,
    ):
        converted = tool_definition_to_openai_tool(tool)
        assert converted["function"]["name"] == tool.name
        assert converted["function"]["parameters"]["additionalProperties"] is False


def test_forbidden_owner_id_rejected() -> None:
    with pytest.raises(ToolValidationError, match="does not accept argument: owner_id"):
        parse_marketing_funnel_get_arguments(
            {"funnel_id": str(uuid4()), "owner_id": str(uuid4())},
        )


@pytest.mark.asyncio
async def test_funnel_get_returns_steps(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9701)
    funnel = await _seed_funnel(db_session, owner, project)
    await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.AWARENESS,
        title="Top of funnel",
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_get",
            name=MARKETING_FUNNEL_GET_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id), "include_steps": True},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert data["funnel"]["id"] == str(funnel.id)
    assert data["funnel"]["steps_count"] == 1
    assert len(data["funnel"]["steps"]) == 1
    assert data["funnel"]["steps"][0]["step_type"] == "awareness"


@pytest.mark.asyncio
async def test_funnel_list_excludes_archived_by_default(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9702)
    active = await _seed_funnel(db_session, owner, project, title="Active funnel")
    archived = await _seed_funnel(db_session, owner, project, title="Archived funnel")
    await MarketingFunnelService(db_session).archive_funnel(
        owner.id,
        project.id,
        archived.id,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_f_list", name=MARKETING_FUNNEL_LIST_TOOL_NAME, arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Active funnel"]
    assert str(active.id) in {item["id"] for item in _tool_data(result)["items"]}


@pytest.mark.asyncio
async def test_step_assets_returns_linked_assets(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9703)
    funnel = await _seed_funnel(db_session, owner, project)
    step = await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.OFFER,
        title="Core Offer",
    )
    asset = await _seed_asset(
        db_session,
        owner,
        project,
        title="Offer page",
        status=ContentAssetStatus.APPROVED,
    )
    linked = await MarketingFunnelService(db_session).link_asset_to_step(
        owner.id,
        project.id,
        funnel.id,
        step.id,
        asset.id,
        role=FunnelStepAssetRole.PRIMARY,
    )
    assert linked is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_assets",
            name=MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
            arguments={"step_id": str(step.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert data["step"]["title"] == "Core Offer"
    assert data["step"]["step_type"] == "offer"
    assert len(data["assets"]) == 1
    assert data["assets"][0]["title"] == "Offer page"
    assert data["assets"][0]["status"] == "approved"
    assert data["assets"][0]["role"] == "primary"


@pytest.mark.asyncio
async def test_ownership_enforced_for_funnel_get(db_session: AsyncSession) -> None:
    owner_a, project_a, agent_a = await _seed_project_with_agent(db_session, telegram_id=9704)
    owner_b = await UserRepository(db_session).create(UserTable(telegram_id=9705))
    project_b = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner_b.id, name="Other funnel project"),
    )
    agent_b = await AgentService(db_session).create_agent(
        owner_b.id,
        AgentCreateRequest(project_id=project_b.id, type=AgentType.STRATEGIST),
    )
    assert agent_b is not None
    funnel = await _seed_funnel(db_session, owner_a, project_a)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_denied",
            name=MARKETING_FUNNEL_GET_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id)},
        ),
        _context(owner_id=owner_b.id, project_id=project_b.id, agent_id=agent_b.id),
    )

    assert result.status == "failed"
    assert result.output["error"]["code"] in {"not_found", "permission_denied"}


@pytest.mark.asyncio
async def test_gap_analysis_detects_missing_steps(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9706)
    funnel = await _seed_funnel(db_session, owner, project)
    await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.OFFER,
        title="Offer",
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_gap",
            name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert "lead_magnet" in data["missing_steps"]
    assert "checkout" in data["missing_steps"]
    assert data["coverage_score"] == 0.25


@pytest.mark.asyncio
async def test_gap_analysis_detects_steps_without_assets(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9707)
    funnel = await _seed_funnel(db_session, owner, project)
    awareness = await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.OFFER,
        title="Offer",
    )
    asset = await _seed_asset(db_session, owner, project, title="Hero")
    await MarketingFunnelService(db_session).link_asset_to_step(
        owner.id,
        project.id,
        funnel.id,
        awareness.id,
        asset.id,
        role=FunnelStepAssetRole.PRIMARY,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_gap_assets",
            name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert "offer" in data["steps_without_assets"]
    assert "awareness" not in data["steps_without_assets"]


def test_coverage_score_calculated() -> None:
    analysis = compute_funnel_gap_analysis(
        steps=[],
        links=[],
        linked_assets_by_id={},
    )
    assert analysis["coverage_score"] == 0.0
    assert len(analysis["missing_steps"]) == 8

    class _Step:
        def __init__(self, step_type: str, status: str = "active") -> None:
            self.id = uuid4()
            self.step_type = type("T", (), {"value": step_type})()
            self.status = type("S", (), {"value": status})()

    steps = [_Step(value) for value in ("awareness", "offer", "checkout", "onboarding")]
    analysis = compute_funnel_gap_analysis(steps=steps, links=[], linked_assets_by_id={})
    assert analysis["coverage_score"] == 0.5


@pytest.mark.asyncio
async def test_gap_analysis_counts_asset_statuses(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9708)
    funnel = await _seed_funnel(db_session, owner, project)
    step = await _seed_step(
        db_session,
        owner,
        project,
        funnel,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    approved = await _seed_asset(
        db_session,
        owner,
        project,
        title="Approved",
        status=ContentAssetStatus.APPROVED,
    )
    draft = await _seed_asset(db_session, owner, project, title="Draft")
    service = MarketingFunnelService(db_session)
    await service.link_asset_to_step(
        owner.id,
        project.id,
        funnel.id,
        step.id,
        approved.id,
        role=FunnelStepAssetRole.PRIMARY,
    )
    await service.link_asset_to_step(
        owner.id,
        project.id,
        funnel.id,
        step.id,
        draft.id,
        role=FunnelStepAssetRole.SUPPORTING,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_f_gap_counts",
            name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    data = _tool_data(result)
    assert data["approved_assets_count"] == 1
    assert data["draft_assets_count"] == 1


@pytest.mark.asyncio
async def test_audit_log_created_on_success(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9709)
    funnel = await _seed_funnel(db_session, owner, project)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(
            id="call_f_audit_ok",
            name=MARKETING_FUNNEL_GET_TOOL_NAME,
            arguments={"funnel_id": str(funnel.id)},
        ),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].tool_name == MARKETING_FUNNEL_GET_TOOL_NAME
    assert logs[0].status == "succeeded"
    assert logs[0].result_preview["ok"] is True


@pytest.mark.asyncio
async def test_audit_log_created_on_failure(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9710)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(
            id="call_f_audit_fail",
            name=MARKETING_FUNNEL_GET_TOOL_NAME,
            arguments={"funnel_id": str(uuid4())},
        ),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].result_preview["error_code"] == "not_found"


def test_agent_run_executor_flow_executes_marketing_funnel_get(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Funnel Get"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Flow funnel", "description": "secret-funnel-desc"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "get funnel",
                "mock_tool_call": {
                    "id": "call_flow_f",
                    "type": "function",
                    "function": {
                        "name": "marketing_funnel.get",
                        "arguments": {"funnel_id": funnel_id, "include_steps": False},
                    },
                },
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["marketing_funnel.get"],
    }
    assert "secret-funnel-desc" not in json.dumps(body["output_payload"])


def test_langgraph_path_can_call_marketing_funnel_gap_analysis(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Graph Funnel Gap"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "analyst"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Gap funnel"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "gap analysis",
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
    assert body["output_payload"]["tools"] == {
        "executed_count": 1,
        "failed_count": 0,
        "tool_names": ["marketing_funnel.gap_analysis"],
    }


def test_tool_profiles_updated() -> None:
    strategist = get_agent_tool_allowlist(AgentType.STRATEGIST)
    analyst = get_agent_tool_allowlist(AgentType.ANALYST)
    planner = get_agent_tool_allowlist(AgentType.CONTENT_PLANNER)
    copywriter = get_agent_tool_allowlist(AgentType.COPYWRITER)

    for name in EXPECTED_FUNNEL_TOOL_NAMES:
        assert name in strategist
        assert name in analyst
        assert name in planner

    assert "marketing_funnel.get" in copywriter
    assert "marketing_funnel.step_assets" in copywriter
    assert "marketing_funnel.list" not in copywriter
    assert "marketing_funnel.gap_analysis" not in copywriter


def test_real_executable_allow_list_contains_funnel_tools() -> None:
    for name in EXPECTED_FUNNEL_TOOL_NAMES:
        assert name in REAL_READ_ONLY_EXECUTABLE_TOOLS
    assert len(REAL_READ_ONLY_EXECUTABLE_TOOLS) == 12

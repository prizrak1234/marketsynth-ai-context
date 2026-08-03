"""Phase 14.1 — review_queue.list read tool."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from app.db.models.project import ProjectTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.registry import get_tool_registry
from app.tools.permissions import ToolExecutionMode, evaluate_tool_access, get_tool_access_mode
from app.tools.review_queue_tools import REVIEW_QUEUE_LIST_TOOL_NAME
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

LEAK_MARKERS = (
    "plan_payload",
    '"body"',
    "body_preview",
    "version_metadata",
    "super-secret",
    "channel_config",
    "delivery",
)

_ALLOWED = (
    AgentType.STRATEGIST,
    AgentType.ORCHESTRATOR,
    AgentType.CONTENT_PLANNER,
    AgentType.ANALYST,
)

_DENIED = (
    AgentType.COPYWRITER,
    AgentType.RESEARCHER,
    AgentType.CRITIC,
)

_ITEM_KEYS = frozenset(
    {
        "type",
        "id",
        "campaign_id",
        "campaign_title",
        "title",
        "status",
        "current_version_number",
        "updated_at",
    },
)


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Draft",
    body: str = "super-secret body",
) -> str:
    resp = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": title, "body": body},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _ctx(*, owner_id: str, project_id: str, agent_type: AgentType) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=UUID(owner_id),
        project_id=UUID(project_id),
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
        request_id=str(uuid4()),
    )


async def _owner_id_for_project(db_session: AsyncSession, project_id: str) -> str:
    row = await db_session.get(ProjectTable, UUID(project_id))
    assert row is not None
    return str(row.owner_id)


@pytest.mark.asyncio
async def test_review_queue_tool_returns_pending_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool pending")
    asset_id = _create_asset(client, auth_headers, project_id, title="Pending")

    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(id="rq_list", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={}),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.STRATEGIST),
    )

    assert result.status == "succeeded"
    data = result.output["data"]
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == asset_id
    assert data["items"][0]["status"] == "draft"
    assert set(data["items"][0].keys()) == _ITEM_KEYS
    assert "created_at" not in data["items"][0]


@pytest.mark.asyncio
async def test_review_queue_tool_excludes_approved_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool approved")
    asset_id = _create_asset(client, auth_headers, project_id, title="Gone")
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(id="rq_empty", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={}),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.ORCHESTRATOR),
    )
    assert result.status == "succeeded"
    data = result.output["data"]
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_review_queue_tool_enforces_owner_project_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool mine")
    other_project_id = _project_id(client, other_auth_headers, "RQ tool other")
    _create_asset(client, other_auth_headers, other_project_id, title="Secret")

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(id="rq_scope", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={}),
        _ctx(owner_id=owner_id, project_id=other_project_id, agent_type=AgentType.ANALYST),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False


@pytest.mark.asyncio
async def test_review_queue_tool_limit(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool limit")
    for index in range(3):
        _create_asset(client, auth_headers, project_id, title=f"Asset {index}")

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(id="rq_lim", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={"limit": 2}),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.CONTENT_PLANNER),
    )
    assert result.status == "succeeded"
    data = result.output["data"]
    assert data["count"] == 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_review_queue_tool_rejects_project_id_argument(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool forbid")
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(
            id="rq_forbid",
            name=REVIEW_QUEUE_LIST_TOOL_NAME,
            arguments={"project_id": project_id},
        ),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.STRATEGIST),
    )
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_review_queue_tool_has_no_content_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool leaks")
    asset_id = _create_asset(client, auth_headers, project_id, body="super-secret")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "version two secret"},
        headers=auth_headers,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(id="rq_leak", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={}),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.STRATEGIST),
    )
    assert result.status == "succeeded"
    blob = json.dumps(result.output).lower()
    for marker in LEAK_MARKERS:
        assert marker.lower() not in blob


@pytest.mark.asyncio
async def test_review_queue_tool_writes_audit_log(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "RQ tool audit")
    _create_asset(client, auth_headers, project_id)

    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    owner_id = await _owner_id_for_project(db_session, project_id)
    await executor.execute(
        ToolCall(id="rq_audit", name=REVIEW_QUEUE_LIST_TOOL_NAME, arguments={}),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.ANALYST),
    )

    logs = await ToolExecutionLogRepository(db_session).list_by_project(
        UUID(owner_id),
        UUID(project_id),
        limit=20,
        offset=0,
    )
    assert any(row.tool_name == REVIEW_QUEUE_LIST_TOOL_NAME for row in logs)


def test_review_queue_tool_allowlist_and_denylist() -> None:
    registry = get_tool_registry()
    tool = registry.get(REVIEW_QUEUE_LIST_TOOL_NAME)
    assert get_tool_access_mode(tool) == ToolExecutionMode.READ_ONLY

    for agent_type in _ALLOWED:
        names = {t.name for t in registry.list_for_agent(agent_type)}
        assert REVIEW_QUEUE_LIST_TOOL_NAME in names
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=REVIEW_QUEUE_LIST_TOOL_NAME,
            tool=tool,
        )
        assert decision.allowed is True

    for agent_type in _DENIED:
        names = {t.name for t in registry.list_for_agent(agent_type)}
        assert REVIEW_QUEUE_LIST_TOOL_NAME not in names
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=REVIEW_QUEUE_LIST_TOOL_NAME,
            tool=tool,
        )
        assert decision.allowed is False


def test_review_queue_approve_tool_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    assert "review_queue.approve" not in registered

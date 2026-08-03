"""Phase 4.1 — marketing read-only tool execution tests."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.db.models.user import UserTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetType
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.content_asset_get import parse_content_asset_get_arguments
from app.tools.executors.marketing_brief_get import parse_marketing_brief_get_arguments
from app.tools.executors.marketing_brief_list import (
    MARKETING_BRIEF_LIST_MAX_LIMIT,
    parse_marketing_brief_list_arguments,
)
from app.tools.marketing_tools import (
    BODY_INCLUDE_MAX_CHARS,
    CONTENT_ASSET_GET_TOOL_NAME,
    CONTENT_ASSET_LIST_TOOL_NAME,
    MARKETING_BRIEF_GET_TOOL_NAME,
    MARKETING_BRIEF_LIST_TOOL_NAME,
)
from app.tools.openai_schema import tool_definition_to_openai_tool
from app.tools.permissions import REAL_READ_ONLY_EXECUTABLE_TOOLS
from app.tools.registry import (
    CONTENT_ASSET_GET_TOOL,
    CONTENT_ASSET_LIST_TOOL,
    MARKETING_BRIEF_GET_TOOL,
    MARKETING_BRIEF_LIST_TOOL,
    get_tool_registry,
)
from app.tools.result_builder import enforce_result_size_limit
from app.tools.result_contracts import ToolExecutionErrorCode
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.researcher_tool_names import (
    RESEARCHER_READ_ONLY_TOOL_NAMES as EXPECTED_RESEARCHER_TOOL_NAMES,
)

EXPECTED_MARKETING_TOOL_NAMES = [
    "content_asset.get",
    "content_asset.list",
    "marketing_brief.get",
    "marketing_brief.list",
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


async def _seed_project_with_agent(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Marketing Tool Project {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST),
    )
    assert agent is not None
    return owner, project, agent


async def _seed_brief(
    db_session: AsyncSession,
    owner,
    project,
    *,
    title: str = "Launch brief",
    offer: str = "Trial offer",
    constraints: dict | None = None,
) -> object:
    row = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title=title,
        offer=offer,
        constraints=constraints or {"tone": "professional"},
    )
    assert row is not None
    return row


async def _seed_asset(
    db_session: AsyncSession,
    owner,
    project,
    *,
    title: str = "Asset",
    body: str = "Hello founders",
    brief_id=None,
    asset_type: ContentAssetType = ContentAssetType.TELEGRAM_POST,
    status: ContentAssetStatus = ContentAssetStatus.DRAFT,
) -> object:
    service = ContentAssetService(db_session)
    row = await service.create(
        owner.id,
        project.id,
        asset_type=asset_type,
        title=title,
        body=body,
        brief_id=brief_id,
        status=ContentAssetStatus.DRAFT,
    )
    assert row is not None
    if status == ContentAssetStatus.APPROVED:
        approved = await service.approve_asset(owner.id, project.id, row.id)
        assert approved is not None
        return approved
    if status == ContentAssetStatus.ARCHIVED:
        archived = await service.archive_asset(owner.id, project.id, row.id)
        assert archived is not None
        return archived
    return row


def test_registry_exposes_four_marketing_read_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.STRATEGIST)
    names = [tool.name for tool in tools]
    for name in EXPECTED_MARKETING_TOOL_NAMES:
        assert name in names


def test_openai_schemas_are_valid() -> None:
    for tool in (
        MARKETING_BRIEF_GET_TOOL,
        MARKETING_BRIEF_LIST_TOOL,
        CONTENT_ASSET_GET_TOOL,
        CONTENT_ASSET_LIST_TOOL,
    ):
        converted = tool_definition_to_openai_tool(tool)
        assert converted["function"]["name"] == tool.name
        assert converted["function"]["parameters"]["additionalProperties"] is False


def test_forbidden_owner_id_and_project_id_rejected() -> None:
    with pytest.raises(ToolValidationError, match="does not accept argument: owner_id"):
        parse_marketing_brief_get_arguments(
            {"brief_id": str(uuid4()), "owner_id": str(uuid4())},
        )
    with pytest.raises(ToolValidationError, match="does not accept argument: project_id"):
        parse_content_asset_get_arguments(
            {"asset_id": str(uuid4()), "project_id": str(uuid4())},
        )
    with pytest.raises(ToolValidationError, match="does not accept argument: task_id"):
        parse_marketing_brief_list_arguments({"task_id": str(uuid4())})


@pytest.mark.asyncio
async def test_marketing_brief_get_returns_envelope_ok_true(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9601)
    brief = await _seed_brief(db_session, owner, project, title="Q2 Launch")

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_mb_get",
            name=MARKETING_BRIEF_GET_TOOL_NAME,
            arguments={"brief_id": str(brief.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert result.status == "succeeded"
    assert result.output["tool"] == MARKETING_BRIEF_GET_TOOL_NAME
    data = _tool_data(result)
    assert data["brief"]["id"] == str(brief.id)
    assert data["brief"]["title"] == "Q2 Launch"
    assert data["brief"]["constraints"] == {"tone": "professional"}


@pytest.mark.asyncio
async def test_marketing_brief_get_not_found_is_safe(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9602)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_mb_missing",
            name=MARKETING_BRIEF_GET_TOOL_NAME,
            arguments={"brief_id": str(uuid4())},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    assert result.status == "failed"
    assert result.output["ok"] is False
    assert result.output["error"]["code"] == ToolExecutionErrorCode.NOT_FOUND.value


@pytest.mark.asyncio
async def test_marketing_brief_list_excludes_archived_by_default(
    db_session: AsyncSession,
) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9603)
    active = await _seed_brief(db_session, owner, project, title="Active brief")
    archived = await _seed_brief(db_session, owner, project, title="Archived brief")
    await MarketingBriefService(db_session).archive(owner.id, project.id, archived.id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_mb_list", name=MARKETING_BRIEF_LIST_TOOL_NAME, arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Active brief"]
    assert str(active.id) in {item["id"] for item in _tool_data(result)["items"]}


@pytest.mark.asyncio
async def test_marketing_brief_list_limit_capped_at_ten(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9604)
    for index in range(12):
        await _seed_brief(db_session, owner, project, title=f"Brief {index}")

    options = parse_marketing_brief_list_arguments({"limit": 25})
    assert options.limit == MARKETING_BRIEF_LIST_MAX_LIMIT


@pytest.mark.asyncio
async def test_content_asset_get_returns_body_preview(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9605)
    asset = await _seed_asset(
        db_session,
        owner,
        project,
        body="x" * 500,
        title="Long body asset",
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_get",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(asset.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    asset_payload = _tool_data(result)["asset"]
    assert "body_preview" in asset_payload
    assert len(asset_payload["body_preview"]) <= 300
    assert "body" not in asset_payload


@pytest.mark.asyncio
async def test_content_asset_get_include_body_false_hides_body(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9606)
    secret_tail = "secret-only-past-preview-window"
    asset = await _seed_asset(
        db_session,
        owner,
        project,
        body=("x" * 350) + secret_tail,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_hide",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(asset.id), "include_body": False},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    asset_payload = _tool_data(result)["asset"]
    assert "body" not in asset_payload
    serialized = json.dumps(asset_payload)
    assert secret_tail not in serialized


@pytest.mark.asyncio
async def test_content_asset_get_include_body_true_truncates_body(
    db_session: AsyncSession,
) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9607)
    long_body = "z" * (BODY_INCLUDE_MAX_CHARS + 500)
    asset = await _seed_asset(db_session, owner, project, body=long_body)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_body",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(asset.id), "include_body": True},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    body = _tool_data(result)["asset"]["body"]
    assert len(body) == BODY_INCLUDE_MAX_CHARS


@pytest.mark.asyncio
async def test_content_asset_list_filters_by_brief_id(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9608)
    brief = await _seed_brief(db_session, owner, project, title="Parent")
    await _seed_asset(db_session, owner, project, brief_id=brief.id, title="Linked")
    await _seed_asset(db_session, owner, project, title="Unlinked")

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_list_brief",
            name=CONTENT_ASSET_LIST_TOOL_NAME,
            arguments={"brief_id": str(brief.id)},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Linked"]


@pytest.mark.asyncio
async def test_content_asset_list_filters_by_type_and_status(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9609)
    await _seed_asset(
        db_session,
        owner,
        project,
        title="Email draft",
        asset_type=ContentAssetType.EMAIL,
        status=ContentAssetStatus.DRAFT,
    )
    await _seed_asset(
        db_session,
        owner,
        project,
        title="Email approved",
        asset_type=ContentAssetType.EMAIL,
        status=ContentAssetStatus.APPROVED,
    )
    await _seed_asset(
        db_session,
        owner,
        project,
        title="Ad copy",
        asset_type=ContentAssetType.AD_COPY,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_filters",
            name=CONTENT_ASSET_LIST_TOOL_NAME,
            arguments={"type": "email", "status": "draft"},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Email draft"]


@pytest.mark.asyncio
async def test_content_asset_list_excludes_archived_by_default(
    db_session: AsyncSession,
) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9610)
    active = await _seed_asset(db_session, owner, project, title="Active asset")
    archived = await _seed_asset(db_session, owner, project, title="Archived asset")
    await ContentAssetService(db_session).archive(owner.id, project.id, archived.id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(id="call_ca_list", name=CONTENT_ASSET_LIST_TOOL_NAME, arguments={}),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )

    titles = [item["title"] for item in _tool_data(result)["items"]]
    assert titles == ["Active asset"]
    assert str(active.id) in {item["id"] for item in _tool_data(result)["items"]}


@pytest.mark.asyncio
async def test_ownership_enforced_for_marketing_brief_get(db_session: AsyncSession) -> None:
    owner_a, project_a, agent_a = await _seed_project_with_agent(db_session, telegram_id=9611)
    owner_b = await UserRepository(db_session).create(UserTable(telegram_id=9612))
    project_b = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner_b.id, name="Other project"),
    )
    agent_b = await AgentService(db_session).create_agent(
        owner_b.id,
        AgentCreateRequest(project_id=project_b.id, type=AgentType.STRATEGIST),
    )
    assert agent_b is not None
    brief = await _seed_brief(db_session, owner_a, project_a, title="Owned by A")

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_mb_denied",
            name=MARKETING_BRIEF_GET_TOOL_NAME,
            arguments={"brief_id": str(brief.id)},
        ),
        _context(owner_id=owner_b.id, project_id=project_b.id, agent_id=agent_b.id),
    )

    assert result.status == "failed"
    assert result.output["error"]["code"] in {
        ToolExecutionErrorCode.NOT_FOUND.value,
        ToolExecutionErrorCode.PERMISSION_DENIED.value,
    }


@pytest.mark.asyncio
async def test_audit_log_created_on_success(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9613)
    brief = await _seed_brief(db_session, owner, project)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(
            id="call_mb_audit_ok",
            name=MARKETING_BRIEF_GET_TOOL_NAME,
            arguments={"brief_id": str(brief.id)},
        ),
        context,
    )
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(
        owner.id,
        context.agent_run_id,
    )
    assert len(logs) == 1
    assert logs[0].tool_name == MARKETING_BRIEF_GET_TOOL_NAME
    assert logs[0].status == "succeeded"
    assert logs[0].result_preview["ok"] is True


@pytest.mark.asyncio
async def test_audit_log_created_on_failure(db_session: AsyncSession) -> None:
    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9614)
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(
        ToolCall(
            id="call_mb_audit_fail",
            name=MARKETING_BRIEF_GET_TOOL_NAME,
            arguments={"brief_id": str(uuid4())},
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


def test_agent_run_executor_flow_executes_marketing_brief_get(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Flow Marketing Brief"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()["id"]
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Flow brief", "offer": "secret-offer-full-text"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "get brief",
                "mock_tool_call": {
                    "id": "call_flow_mb",
                    "type": "function",
                    "function": {
                        "name": "marketing_brief.get",
                        "arguments": {"brief_id": brief_id},
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
        "tool_names": ["marketing_brief.get"],
    }
    assert "secret-offer-full-text" not in json.dumps(body["output_payload"])


def test_langgraph_path_can_call_content_asset_list(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Graph Marketing List"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Listed in graph", "body": "graph-secret-body"},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": {
                "prompt": "list assets",
                "mock_tool_call": {
                    "id": "call_graph_ca_list",
                    "type": "function",
                    "function": {
                        "name": "content_asset.list",
                        "arguments": {"limit": 5},
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
        "tool_names": ["content_asset.list"],
    }
    assert "graph-secret-body" not in json.dumps(body["output_payload"])


@pytest.mark.asyncio
async def test_result_preview_compact_without_full_body_leak(
    db_session: AsyncSession,
) -> None:
    from app.tools.audit_preview import build_audit_preview

    owner, project, agent = await _seed_project_with_agent(db_session, telegram_id=9615)
    asset = await _seed_asset(
        db_session,
        owner,
        project,
        body="leak-me-" + ("x" * 2000),
    )
    context = _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id)
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    result = await executor.execute(
        ToolCall(
            id="call_preview",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(asset.id), "include_body": True},
        ),
        context,
    )
    preview = build_audit_preview(
        ToolCall(
            id="call_preview",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(asset.id), "include_body": True},
        ),
        result,
    ).result_preview
    serialized = json.dumps(preview)
    assert "leak-me-" not in serialized
    assert preview.get("items_count") == 1 or preview.get("ok") is True


def test_tool_count_expectations_for_researcher() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.RESEARCHER)
    assert [tool.name for tool in tools] == EXPECTED_RESEARCHER_TOOL_NAMES
    assert len(REAL_READ_ONLY_EXECUTABLE_TOOLS) == 17


def test_real_executable_allow_list_contains_marketing_tools() -> None:
    for name in EXPECTED_MARKETING_TOOL_NAMES:
        assert name in REAL_READ_ONLY_EXECUTABLE_TOOLS


def test_enforce_result_size_limit_applies_after_marketing_body_include() -> None:
    from app.tools.result_builder import build_tool_success

    envelope = build_tool_success(
        CONTENT_ASSET_GET_TOOL_NAME,
        {
            "asset": {
                "id": str(uuid4()),
                "body": "x" * BODY_INCLUDE_MAX_CHARS,
                "body_preview": "x" * 300,
            },
            "count": 1,
        },
    )
    limited = enforce_result_size_limit(envelope, max_bytes=512)
    assert limited["ok"] is False
    assert limited["error"]["code"] == ToolExecutionErrorCode.RESULT_TOO_LARGE.value

"""Phase 12.2 — asset revision tools readiness invariants (freeze guard)."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.db.models.project import ProjectTable
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.asset_read_settings import (
    CAMPAIGN_ASSET_LIST_TOOL_NAME,
    CONTENT_ASSET_GET_BODY_ALLOWED_AGENT_TYPES,
)
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.content_asset_create_revision import (
    parse_content_asset_create_revision_arguments,
)
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_REVISION_PARAMETERS_SCHEMA,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CONTENT_ASSET_GET_TOOL_NAME,
    CONTENT_ASSET_LIST_TOOL_NAME,
    CREATE_REVISION_FORBIDDEN_ARGUMENT_KEYS,
    format_content_asset_compact,
    format_content_asset_create_revision_result,
    format_content_asset_full,
)
from app.tools.permissions import (
    REAL_READ_ONLY_EXECUTABLE_TOOLS,
    is_real_read_only_executable,
)
from app.tools.registry import (
    CAMPAIGN_ASSET_LIST_TOOL,
    CONTENT_ASSET_CREATE_REVISION_TOOL,
    CONTENT_ASSET_GET_TOOL,
    CONTENT_ASSET_LIST_TOOL,
    get_tool_registry,
)
from app.tools.write_tool_settings import (
    CREATE_REVISION_ALLOWED_AGENT_TYPES,
    content_asset_create_revision_enabled,
    is_write_tool_visible_to_agent,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

PHASE_12_FORBIDDEN_AGENT_TOOLS = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.schedule",
        "publication_job.create",
        "publication_job.schedule",
        "campaign_plan_draft.generate_assets",
    },
)

READ_ONLY_ASSET_TOOL_NAMES = frozenset(
    {
        CONTENT_ASSET_GET_TOOL_NAME,
        CONTENT_ASSET_LIST_TOOL_NAME,
        CAMPAIGN_ASSET_LIST_TOOL_NAME,
    },
)

COMPACT_REVISION_RESULT_KEYS = frozenset(
    {
        "asset_id",
        "status",
        "current_version_number",
        "approved_version_number",
    },
)


@pytest.fixture
def revision_flags_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    body: str = "v1",
    brief_id: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    payload: dict = {"type": "email", "title": "Asset", "body": body}
    if brief_id is not None:
        payload["brief_id"] = brief_id
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    resp = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _approve(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str) -> dict:
    resp = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _owner_id(db_session: AsyncSession, project_id: str) -> UUID:
    row = await db_session.get(ProjectTable, UUID(project_id))
    assert row is not None
    return row.owner_id


async def _job_count(db_session: AsyncSession, *, owner_id: UUID, project_id: UUID) -> int:
    statement = select(func.count()).where(
        PublicationJobTable.owner_id == owner_id,
        PublicationJobTable.project_id == project_id,
    )
    result = await db_session.execute(statement)
    return int(result.scalar_one())


def _ctx(owner_id: UUID, project_id: UUID, agent_type: AgentType) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
        request_id=str(uuid4()),
    )


def test_invariant_read_only_asset_tools_registered_as_read_only() -> None:
    for tool in (CONTENT_ASSET_GET_TOOL, CONTENT_ASSET_LIST_TOOL, CAMPAIGN_ASSET_LIST_TOOL):
        assert tool.metadata.get("access_mode") == "read_only"
        assert tool.metadata.get("execution_mode") == "read_only"
    for name in READ_ONLY_ASSET_TOOL_NAMES:
        assert is_real_read_only_executable(name)
        assert name in REAL_READ_ONLY_EXECUTABLE_TOOLS


def test_invariant_create_revision_registered_as_write_only() -> None:
    assert CONTENT_ASSET_CREATE_REVISION_TOOL.metadata.get("access_mode") == "write"
    assert CONTENT_ASSET_CREATE_REVISION_TOOL.metadata.get("execution_mode") == "write"
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME not in REAL_READ_ONLY_EXECUTABLE_TOOLS


def test_invariant_forbidden_approve_publish_schedule_tools_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in PHASE_12_FORBIDDEN_AGENT_TOOLS:
        assert forbidden not in registered
    for forbidden in (
        "content_asset.approve",
        "content_asset.publish",
    ):
        assert forbidden in FORBIDDEN_AGENT_TOOL_NAMES


def test_invariant_create_revision_hidden_when_flags_off() -> None:
    assert content_asset_create_revision_enabled() is False
    for agent_type in AgentType:
        assert not is_write_tool_visible_to_agent(
            agent_type,
            CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
        )


_ALLOWED_REVISION_TYPES = sorted(
    CREATE_REVISION_ALLOWED_AGENT_TYPES,
    key=lambda t: t.value,
)


@pytest.mark.parametrize("agent_type", _ALLOWED_REVISION_TYPES)
def test_invariant_create_revision_visible_only_for_allowed_types_when_enabled(
    agent_type: AgentType,
    revision_flags_on: None,
) -> None:
    assert is_write_tool_visible_to_agent(agent_type, CONTENT_ASSET_CREATE_REVISION_TOOL_NAME)
    tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME in tools


@pytest.mark.parametrize("agent_type", [AgentType.ANALYST, AgentType.RESEARCHER])
def test_invariant_analyst_and_researcher_never_see_create_revision(
    agent_type: AgentType,
    revision_flags_on: None,
) -> None:
    assert not is_write_tool_visible_to_agent(
        agent_type,
        CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    )
    tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME not in tools


def test_invariant_revision_schema_blocks_status_campaign_brief_reassignment() -> None:
    props = set(CONTENT_ASSET_CREATE_REVISION_PARAMETERS_SCHEMA["properties"])
    assert "campaign_id" not in props
    assert "brief_id" not in props
    assert "status" not in props
    for key in ("campaign_id", "brief_id", "status", "source_agent_run_id"):
        assert key in CREATE_REVISION_FORBIDDEN_ARGUMENT_KEYS


def test_invariant_source_agent_run_id_not_accepted_in_tool_arguments() -> None:
    with pytest.raises(ToolValidationError, match="source_agent_run_id"):
        parse_content_asset_create_revision_arguments(
            {
                "project_id": str(uuid4()),
                "asset_id": str(uuid4()),
                "body": "text",
                "source_agent_run_id": str(uuid4()),
            },
        )


def test_invariant_revision_executor_uses_run_context_for_agent_run_id() -> None:
    from app.tools.executors import content_asset_create_revision as revision_module

    source = inspect.getsource(revision_module.ContentAssetCreateRevisionToolExecutor.execute)
    assert "created_by_agent_run_id=context.agent_run_id" in source.replace(" ", "")


def test_invariant_compact_outputs_exclude_full_body_and_versions() -> None:
    class _Row:
        id = uuid4()
        project_id = uuid4()
        status = type("S", (), {"value": "draft"})()
        current_version_number = 2
        approved_version_number = None
        body = "secret full body must not appear"
        asset_metadata = {"k": "v"}
        brief_id = None
        campaign_id = None
        task_id = None
        agent_run_id = None
        asset_type = type("T", (), {"value": "email"})()
        title = "T"
        created_at = type("DT", (), {"isoformat": lambda self: "2026-01-01T00:00:00"})()
        updated_at = created_at
        source_asset_id = None
        source_version_number = None
        revision_number = None

    row = _Row()
    compact = format_content_asset_compact(row)
    assert "body" not in compact
    assert "body_preview" in compact
    assert "versions" not in compact

    full = format_content_asset_full(row, include_body=True)
    assert "body" in full
    assert "versions" not in full

    revision = format_content_asset_create_revision_result(row)
    assert set(revision.keys()) == COMPACT_REVISION_RESULT_KEYS
    assert "body" not in revision
    assert "versions" not in revision


@pytest.mark.asyncio
async def test_invariant_approved_revision_preserves_source_approved_version(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    revision_flags_on: None,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv approved")
    source = _create_asset(client, auth_headers, project_id)
    _approve(client, auth_headers, project_id, source["id"])

    owner_id = await _owner_id(db_session, project_id)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_rev_approved",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                "project_id": project_id,
                "asset_id": source["id"],
                "body": "revision body",
            },
        ),
        _ctx(owner_id, UUID(project_id), AgentType.COPYWRITER),
    )
    assert result.status == "succeeded"

    source_after = client.get(
        f"/projects/{project_id}/content-assets/{source['id']}",
        headers=auth_headers,
    ).json()
    assert source_after["approved_version_number"] == 1
    assert source_after["status"] == "approved"


@pytest.mark.asyncio
async def test_invariant_draft_revision_does_not_create_publication_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    revision_flags_on: None,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv jobs")
    asset = _create_asset(client, auth_headers, project_id)
    owner_id = await _owner_id(db_session, project_id)
    before = await _job_count(db_session, owner_id=owner_id, project_id=UUID(project_id))

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    await executor.execute(
        ToolCall(
            id="inv_rev_jobs",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                "project_id": project_id,
                "asset_id": asset["id"],
                "body": "updated",
            },
        ),
        _ctx(owner_id, UUID(project_id), AgentType.COPYWRITER),
    )

    after = await _job_count(db_session, owner_id=owner_id, project_id=UUID(project_id))
    assert after == before


@pytest.mark.asyncio
async def test_invariant_archived_asset_revision_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    revision_flags_on: None,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv archived")
    asset = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/archive",
        headers=auth_headers,
    )

    owner_id = await _owner_id(db_session, project_id)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_rev_archived",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                "project_id": project_id,
                "asset_id": asset["id"],
                "body": "nope",
            },
        ),
        _ctx(owner_id, UUID(project_id), AgentType.COPYWRITER),
    )
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_invariant_draft_revision_preserves_campaign_and_brief(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    revision_flags_on: None,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv links")
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "B"},
        headers=auth_headers,
    ).json()["id"]
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "C", "status": "active", "brief_id": brief_id},
        headers=auth_headers,
    ).json()["id"]
    asset = _create_asset(
        client,
        auth_headers,
        project_id,
        brief_id=brief_id,
        campaign_id=campaign_id,
    )

    owner_id = await _owner_id(db_session, project_id)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_rev_links",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                "project_id": project_id,
                "asset_id": asset["id"],
                "body": "linked revision",
            },
        ),
        _ctx(owner_id, UUID(project_id), AgentType.CONTENT_PLANNER),
    )
    assert result.status == "succeeded"

    refreshed = client.get(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        headers=auth_headers,
    ).json()
    assert refreshed["brief_id"] == brief_id
    assert refreshed["campaign_id"] == campaign_id


@pytest.mark.asyncio
async def test_invariant_revision_writes_audit_log(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    revision_flags_on: None,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv audit")
    asset = _create_asset(client, auth_headers, project_id)
    owner_id = await _owner_id(db_session, project_id)

    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    await executor.execute(
        ToolCall(
            id="inv_rev_audit",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                "project_id": project_id,
                "asset_id": asset["id"],
                "body": "audited",
            },
        ),
        _ctx(owner_id, UUID(project_id), AgentType.CRITIC),
    )

    logs = await ToolExecutionLogRepository(db_session).list_by_project(
        owner_id,
        UUID(project_id),
        limit=20,
        offset=0,
    )
    assert any(row.tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME for row in logs)


@pytest.mark.asyncio
async def test_invariant_read_list_output_has_no_full_body(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 inv read compact")
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "C", "status": "active"},
        headers=auth_headers,
    ).json()["id"]
    _create_asset(
        client,
        auth_headers,
        project_id,
        body="x" * 500,
        campaign_id=campaign_id,
    )

    owner_id = await _owner_id(db_session, project_id)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_list",
            name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
            arguments={"campaign_id": campaign_id, "limit": 5},
        ),
        _ctx(owner_id, UUID(project_id), AgentType.STRATEGIST),
    )
    assert result.status == "succeeded"
    items = result.output["data"]["items"]
    assert len(items) >= 1
    for item in items:
        assert "body" not in item
        assert "body_preview" in item
        assert "versions" not in item


def test_invariant_get_body_allowlist_matches_policy() -> None:
    assert AgentType.ANALYST not in CONTENT_ASSET_GET_BODY_ALLOWED_AGENT_TYPES
    assert AgentType.COPYWRITER in CONTENT_ASSET_GET_BODY_ALLOWED_AGENT_TYPES

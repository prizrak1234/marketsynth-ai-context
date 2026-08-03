"""Phase 12.1 — content_asset.create_revision gated write tool."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import ContentAssetVersionSource
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.result_contracts import ToolExecutionErrorCode
from app.tools.write_tool_settings import CREATE_REVISION_ALLOWED_AGENT_TYPES
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publishing import PublicationJobTable


@pytest.fixture
def enable_create_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(
    *,
    owner_id,
    project_id,
    agent_id,
    agent_type: AgentType = AgentType.COPYWRITER,
    agent_run_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=agent_run_id or uuid4(),
    )


def _tool_arguments(*, project_id, asset_id, body: str, title: str | None = None) -> dict:
    payload: dict = {
        "project_id": str(project_id),
        "asset_id": str(asset_id),
        "body": body,
    }
    if title is not None:
        payload["title"] = title
    return payload


async def _publication_job_count(
    db_session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
) -> int:
    statement = select(func.count()).where(
        PublicationJobTable.owner_id == owner_id,
        PublicationJobTable.project_id == project_id,
    )
    result = await db_session.execute(statement)
    return int(result.scalar_one())


async def _owner_id_for_project(db_session: AsyncSession, project_id: str) -> UUID:
    row = await db_session.get(ProjectTable, UUID(project_id))
    assert row is not None
    return row.owner_id


async def _agent_run_for_owner_project(
    db_session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    telegram_id: int,
):
    agent = await AgentService(db_session).create_agent(
        owner_id,
        AgentCreateRequest(project_id=project_id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    run = await AgentRunService(db_session).create_run(
        owner_id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "revise"},
        metadata={},
    )
    assert run is not None
    return agent, run


async def _seed_copywriter(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Revision Tool {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "revise"},
        metadata={},
    )
    assert run is not None
    return owner, project, agent, run


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "Rev tool"}, headers=headers).json()["id"]


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Asset",
    body: str = "draft body v1",
    brief_id: str | None = None,
    campaign_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    payload: dict = {"type": "email", "title": title, "body": body}
    if brief_id is not None:
        payload["brief_id"] = brief_id
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    if metadata is not None:
        payload["metadata"] = metadata
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approve(client: TestClient, headers: dict[str, str], project_id: str, asset_id: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_revision_tool_hidden_when_flags_off() -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.COPYWRITER)}
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME not in tools


@pytest.mark.asyncio
async def test_disabled_global_write_flag_rejected(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()

    owner, project, agent, run = await _seed_copywriter(db_session, telegram_id=12001)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_global_off",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project.id,
                asset_id=uuid4(),
                body="new body",
            ),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    if isinstance(result.output, dict) and result.output.get("error"):
        assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata.get("reason") in {
        "write_tools_disabled",
        "write_tool_disabled",
        "tool_not_in_allowlist",
    }
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_disabled_specific_flag_rejected(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED", "false")
    get_settings.cache_clear()

    owner, project, agent, run = await _seed_copywriter(db_session, telegram_id=12002)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_specific_off",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project.id,
                asset_id=uuid4(),
                body="new body",
            ),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.metadata["reason"] == "write_tool_disabled"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_success_for_draft_asset_increments_version(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id, body="version one")
    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12003,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_draft",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=asset["id"],
                body="version two from agent",
                title="Revised title",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    payload = _tool_data(result)
    assert payload["asset_id"] == asset["id"]
    assert payload["status"] == "draft"
    assert payload["current_version_number"] == 2
    assert payload["approved_version_number"] is None

    versions = ContentAssetVersionRepository(db_session)
    rows = await versions.list_versions(UUID(asset["id"]), owner_id, UUID(project_id))
    assert len(rows) == 2
    assert rows[1].body == "version two from agent"
    assert rows[1].created_by_source == ContentAssetVersionSource.AGENT_TOOL
    assert rows[1].created_by_agent_run_id == run.id
    assert rows[1].version_metadata.get("source_agent_run_id") == str(run.id)


@pytest.mark.asyncio
async def test_success_for_approved_asset_preserves_source_approved_version(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    source = _create_asset(client, auth_headers, project_id, body="approved original")
    approved = _approve(client, auth_headers, project_id, source["id"])
    assert approved["approved_version_number"] == 1

    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12004,
    )
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_approved",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=source["id"],
                body="revision draft body",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    revision = _tool_data(result)
    assert revision["asset_id"] != source["id"]
    assert revision["status"] == "draft"
    assert revision["approved_version_number"] is None

    source_after = client.get(
        f"/projects/{project_id}/content-assets/{source['id']}",
        headers=auth_headers,
    ).json()
    assert source_after["approved_version_number"] == 1
    assert source_after["status"] == "approved"


@pytest.mark.asyncio
async def test_archived_asset_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/archive",
        headers=auth_headers,
    )

    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12005,
    )
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_archived",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=asset["id"],
                body="should fail",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.output["ok"] is False


@pytest.mark.asyncio
async def test_secret_metadata_patch_rejected(
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    owner, project, agent, run = await _seed_copywriter(db_session, telegram_id=12006)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_secret_meta",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments={
                **_tool_arguments(
                    project_id=project.id,
                    asset_id=uuid4(),
                    body="clean body",
                ),
                "metadata_patch": {"api_key": "sk-secret"},
            },
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


@pytest.mark.asyncio
async def test_secret_body_rejected(
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    owner, project, agent, run = await _seed_copywriter(db_session, telegram_id=12007)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_secret_body",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project.id,
                asset_id=uuid4(),
                body="token bearer abcdef",
            ),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


@pytest.mark.asyncio
async def test_foreign_project_asset_access_denied(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    other_project_id = _project_id(client, other_auth_headers)
    other_asset = _create_asset(client, other_auth_headers, other_project_id)

    project_id = _project_id(client, auth_headers)
    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12008,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_foreign",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=other_asset["id"],
                body="stolen edit",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] in {
        ToolExecutionErrorCode.NOT_FOUND.value,
        ToolExecutionErrorCode.PERMISSION_DENIED.value,
    }


@pytest.mark.asyncio
async def test_campaign_and_brief_ids_unchanged_on_draft_revision(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief"},
        headers=auth_headers,
    ).json()["id"]
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "Camp", "status": "active", "brief_id": brief_id},
        headers=auth_headers,
    ).json()["id"]
    asset = _create_asset(
        client,
        auth_headers,
        project_id,
        brief_id=brief_id,
        campaign_id=campaign_id,
    )

    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12009,
    )
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_rev_links",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=asset["id"],
                body="updated copy",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"

    refreshed = client.get(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        headers=auth_headers,
    ).json()
    assert refreshed["brief_id"] == brief_id
    assert refreshed["campaign_id"] == campaign_id


@pytest.mark.asyncio
async def test_no_publication_jobs_created(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)

    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12010,
    )
    jobs_before = await _publication_job_count(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    await executor.execute(
        ToolCall(
            id="call_rev_no_jobs",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=asset["id"],
                body="no scheduling here",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )

    jobs_after = await _publication_job_count(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
    )
    assert jobs_after == jobs_before


@pytest.mark.asyncio
async def test_audit_log_written(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    enable_create_revision: None,
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    owner_id = await _owner_id_for_project(db_session, project_id)
    agent, run = await _agent_run_for_owner_project(
        db_session,
        owner_id=owner_id,
        project_id=UUID(project_id),
        telegram_id=12011,
    )

    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    await executor.execute(
        ToolCall(
            id="call_rev_audit",
            name=CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
            arguments=_tool_arguments(
                project_id=project_id,
                asset_id=asset["id"],
                body="audited revision",
            ),
        ),
        _context(
            owner_id=owner_id,
            project_id=UUID(project_id),
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )

    logs = await ToolExecutionLogRepository(db_session).list_by_project(
        owner_id,
        UUID(project_id),
        limit=10,
        offset=0,
    )
    assert any(row.tool_name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME for row in logs)


@pytest.mark.parametrize(
    "agent_type",
    [AgentType.ANALYST, AgentType.RESEARCHER],
)
def test_analyst_and_researcher_do_not_see_create_revision_tool(
    agent_type: AgentType,
    enable_create_revision: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert CONTENT_ASSET_CREATE_REVISION_TOOL_NAME not in tools


def test_allowed_agent_types_include_copywriter_not_analyst() -> None:
    assert AgentType.COPYWRITER in CREATE_REVISION_ALLOWED_AGENT_TYPES
    assert AgentType.ANALYST not in CREATE_REVISION_ALLOWED_AGENT_TYPES
    assert AgentType.RESEARCHER not in CREATE_REVISION_ALLOWED_AGENT_TYPES

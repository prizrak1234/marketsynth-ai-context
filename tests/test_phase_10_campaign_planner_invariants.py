"""Phase 10.3 — campaign planner tools readiness invariants (freeze guard)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES
from app.core.config import get_settings
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import MarketingCampaignStatus
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.marketing_campaign_service import MarketingCampaignService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.executors.campaign_plan_draft_create import (
    parse_campaign_plan_draft_create_arguments,
)
from app.tools.marketing_tools import CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
from app.tools.permissions import (
    READ_ONLY_TOOL_NAMES,
    REAL_READ_ONLY_EXECUTABLE_TOOLS,
    ToolExecutionMode,
    get_tool_access_mode,
)
from app.tools.registry import get_tool_registry
from app.tools.result_contracts import ToolExecutionErrorCode
from app.tools.write_tool_settings import (
    CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES,
    campaign_plan_draft_create_enabled,
    is_write_tool_visible_to_agent,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

CAMPAIGN_READ_ONLY_TOOLS = frozenset(
    {
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "publication_calendar.list",
    },
)

PLAN_DRAFT_ALLOWED_TYPES = frozenset(CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES)
PLAN_DRAFT_DENIED_TYPES = frozenset(
    {
        AgentType.COPYWRITER,
        AgentType.ANALYST,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
    },
)

PHASE_10_FORBIDDEN_WRITE_TOOLS = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "asset.create_from_plan",
        "campaign_plan_draft.publish",
        "publication_job.create",
        "publication_job.schedule",
    },
)


@pytest.fixture
def plan_draft_write_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _sample_plan_payload() -> dict:
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": [
            {
                "title": "Post",
                "channel": "telegram",
                "format": "text",
            },
        ],
    }


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


async def _owner_id_for_project(db_session: AsyncSession, project_id: str) -> str:
    row = await db_session.get(ProjectTable, UUID(project_id))
    assert row is not None
    return str(row.owner_id)


def test_invariant_campaign_read_tools_are_read_only_in_registry() -> None:
    registry = get_tool_registry()
    for name in CAMPAIGN_READ_ONLY_TOOLS:
        assert name in READ_ONLY_TOOL_NAMES
        assert name in REAL_READ_ONLY_EXECUTABLE_TOOLS
        tool = registry.get(name)
        assert get_tool_access_mode(tool) == ToolExecutionMode.READ_ONLY
        assert tool.metadata.get("access_mode") in {"read_only", None} or (
            tool.metadata.get("execution_mode") == "read_only"
        )


def test_invariant_plan_draft_create_hidden_when_global_write_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()
    try:
        for agent_type in PLAN_DRAFT_ALLOWED_TYPES:
            tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
            assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME not in tools
        assert not campaign_plan_draft_create_enabled()
    finally:
        get_settings.cache_clear()


def test_invariant_plan_draft_create_hidden_when_specific_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "false")
    get_settings.cache_clear()
    try:
        for agent_type in PLAN_DRAFT_ALLOWED_TYPES:
            tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
            assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME not in tools
        assert not campaign_plan_draft_create_enabled()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("agent_type", sorted(PLAN_DRAFT_ALLOWED_TYPES, key=lambda t: t.value))
def test_invariant_plan_draft_create_visible_for_allowed_types_when_enabled(
    agent_type: AgentType,
    plan_draft_write_on: None,
) -> None:
    assert is_write_tool_visible_to_agent(agent_type, CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME)
    tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME in tools


@pytest.mark.parametrize("agent_type", sorted(PLAN_DRAFT_DENIED_TYPES, key=lambda t: t.value))
def test_invariant_plan_draft_create_not_visible_for_denied_types(
    agent_type: AgentType,
    plan_draft_write_on: None,
) -> None:
    assert not is_write_tool_visible_to_agent(agent_type, CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME)
    tools = {t.name for t in get_tool_registry().list_for_agent(agent_type)}
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME not in tools


def test_invariant_phase_10_forbidden_write_tools_not_registered() -> None:
    registered = {tool.name for tool in get_tool_registry().list_registered()}
    for forbidden in PHASE_10_FORBIDDEN_WRITE_TOOLS:
        assert forbidden not in registered
    assert "content_asset.approve" in FORBIDDEN_AGENT_TOOL_NAMES
    assert "content_asset.publish" in FORBIDDEN_AGENT_TOOL_NAMES


def test_invariant_create_tool_rejects_source_agent_run_id_in_input() -> None:
    with pytest.raises(ToolValidationError, match="source_agent_run_id"):
        parse_campaign_plan_draft_create_arguments(
            {
                "project_id": str(uuid4()),
                "campaign_id": str(uuid4()),
                "title": "Plan",
                "plan_payload": _sample_plan_payload(),
                "source_agent_run_id": str(uuid4()),
            },
        )


@pytest.mark.asyncio
async def test_invariant_create_tool_writes_audit_log_and_compact_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    plan_draft_write_on: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "P10 inv audit"},
        headers=auth_headers,
    ).json()["id"]
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": "C1", "status": "active"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()["id"]
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "plan"}},
        headers=auth_headers,
    ).json()["id"]

    owner_id = await _owner_id_for_project(db_session, project_id)
    context = ToolExecutionContext(
        owner_id=UUID(owner_id),
        project_id=UUID(project_id),
        agent_id=UUID(agent_id),
        agent_type=AgentType.STRATEGIST,
        agent_run_id=UUID(run_id),
    )
    tool_call = ToolCall(
        id="inv_plan_create",
        name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
        arguments={
            "project_id": project_id,
            "campaign_id": campaign_id,
            "title": "June plan",
            "plan_payload": _sample_plan_payload(),
        },
    )
    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    result = await executor.execute(tool_call, context)
    assert result.status == "succeeded"

    draft = _tool_data(result)["draft"]
    assert set(draft.keys()) == {"draft_id", "campaign_id", "status", "created_at"}
    blob = json.dumps(result.output)
    assert "plan_payload" not in blob
    assert "content_items" not in blob

    await db_session.commit()
    logs = await ToolExecutionLogRepository(db_session).list_by_run(UUID(owner_id), UUID(run_id))
    assert len(logs) == 1
    assert logs[0].tool_name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
    assert logs[0].execution_mode == "write"
    assert "source_agent_run_id" not in json.dumps(logs[0].arguments_preview)


@pytest.mark.asyncio
async def test_invariant_create_tool_rejects_secret_payload(
    db_session: AsyncSession,
    plan_draft_write_on: None,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=11001))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Secret inv"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST),
    )
    assert agent is not None
    campaign = await MarketingCampaignService(db_session).create(
        owner.id,
        project.id,
        brief_id=None,
        title="C",
        description=None,
        status=MarketingCampaignStatus.ACTIVE,
        start_at=None,
        end_at=None,
        campaign_metadata={},
    )
    assert campaign is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "x"},
        metadata={},
    )
    assert run is not None

    payload = _sample_plan_payload()
    payload["api_key"] = "leak"

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_secret",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments={
                "project_id": str(project.id),
                "campaign_id": str(campaign.id),
                "title": "Bad",
                "plan_payload": payload,
            },
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.STRATEGIST,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value


@pytest.mark.asyncio
async def test_invariant_create_tool_does_not_create_assets_or_jobs(
    db_session: AsyncSession,
    plan_draft_write_on: None,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=11002))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="No side effects"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.CONTENT_PLANNER),
    )
    assert agent is not None
    campaign = await MarketingCampaignService(db_session).create(
        owner.id,
        project.id,
        brief_id=None,
        title="C",
        description=None,
        status=MarketingCampaignStatus.ACTIVE,
        start_at=None,
        end_at=None,
        campaign_metadata={},
    )
    assert campaign is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "plan"},
        metadata={},
    )
    assert run is not None

    assets_before = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    jobs_before = await PublicationJobRepository(db_session).list_for_project(
        project.id,
        owner_id=owner.id,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="inv_no_assets",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments={
                "project_id": str(project.id),
                "campaign_id": str(campaign.id),
                "title": "Plan only",
                "plan_payload": _sample_plan_payload(),
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

    assets_after = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    jobs_after = await PublicationJobRepository(db_session).list_for_project(
        project.id,
        owner_id=owner.id,
    )
    assert len(assets_after) == len(assets_before)
    assert len(jobs_after) == len(jobs_before)


@pytest.mark.asyncio
async def test_invariant_read_only_campaign_tools_do_not_leak_sensitive_fields(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "P10 inv leaks"},
        headers=auth_headers,
    ).json()["id"]
    campaign_id = client.post(
        f"/projects/{project_id}/campaigns",
        json={
            "title": "C leak",
            "status": "active",
            "campaign_metadata": {"secret": "nope"},
        },
        headers=auth_headers,
    ).json()["id"]
    channel_id = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Ch", "type": "custom", "config": {"token": "super-secret"}},
        headers=auth_headers,
    ).json()["id"]
    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "A1",
            "body": "Body with sk-secret-token",
            "campaign_id": campaign_id,
        },
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/approve",
        headers=auth_headers,
    )
    scheduled_at = (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={
            "asset_id": asset["id"],
            "channel_id": channel_id,
            "scheduled_at": scheduled_at,
        },
        headers=auth_headers,
    )

    owner_id = await _owner_id_for_project(db_session, project_id)
    context = ToolExecutionContext(
        owner_id=UUID(owner_id),
        project_id=UUID(project_id),
        agent_id=uuid4(),
        agent_type=AgentType.STRATEGIST,
        agent_run_id=uuid4(),
    )
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)

    calls = [
        ToolCall(id="r1", name="marketing_campaign.list", arguments={"limit": 5}),
        ToolCall(
            id="r2",
            name="marketing_campaign.get",
            arguments={"campaign_id": campaign_id},
        ),
        ToolCall(
            id="r3",
            name="marketing_campaign.overview",
            arguments={"campaign_id": campaign_id},
        ),
        ToolCall(
            id="r4",
            name="publication_calendar.list",
            arguments={"campaign_id": campaign_id, "limit": 5},
        ),
    ]
    for call in calls:
        result = await executor.execute(call, context)
        assert result.status == "succeeded"
        blob = str(result.output).lower()
        for forbidden in (
            "sk-secret",
            "super-secret",
            "channel_config",
            "delivery",
            "campaign_metadata",
            "token",
        ):
            assert forbidden not in blob

"""Phase 10.2 — campaign_plan_draft.create gated write tool."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.campaign_plan_drafts import CampaignPlanDraftRepository
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import MarketingCampaignStatus
from app.marketing.plan_payload_validation import PLAN_PAYLOAD_MAX_JSON_BYTES
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
from app.tools.permissions import WRITE_TOOL_NAMES
from app.tools.registry import get_tool_registry
from app.tools.result_contracts import ToolExecutionErrorCode
from app.tools.write_tool_settings import CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def enable_plan_draft_create(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
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
    agent_type: AgentType = AgentType.STRATEGIST,
    agent_run_id=None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=agent_type,
        agent_run_id=agent_run_id or uuid4(),
    )


def _sample_plan_payload() -> dict:
    return {
        "goal": "Launch summer offer",
        "target_audience": "SMB owners",
        "key_message": "Save time with automation",
        "content_items": [
            {
                "title": "Teaser post",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": "Keep it short",
            },
        ],
    }


def _tool_arguments(*, project_id, campaign_id, title: str = "June plan") -> dict:
    return {
        "project_id": str(project_id),
        "campaign_id": str(campaign_id),
        "title": title,
        "plan_payload": _sample_plan_payload(),
    }


async def _seed_strategist_project(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Plan Draft Tool {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST),
    )
    assert agent is not None
    return owner, project, agent


async def _seed_agent_run(db_session: AsyncSession, owner, agent):
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "plan"},
        metadata={},
    )
    assert run is not None
    return run


async def _seed_campaign(db_session: AsyncSession, owner, project):
    campaign = await MarketingCampaignService(db_session).create(
        owner.id,
        project.id,
        brief_id=None,
        title="Campaign",
        description=None,
        status=MarketingCampaignStatus.ACTIVE,
        start_at=None,
        end_at=None,
        campaign_metadata={},
    )
    assert campaign is not None
    return campaign


def test_plan_draft_create_tool_not_visible_when_globally_disabled() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.STRATEGIST)
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME not in {tool.name for tool in tools}


def test_plan_draft_create_disabled_by_default_in_settings() -> None:
    settings = get_settings()
    assert settings.agent_write_tools_enabled is False
    assert settings.agent_write_tool_campaign_plan_draft_create_enabled is False


@pytest.mark.asyncio
async def test_disabled_global_write_flag_rejected(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "false")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "true")
    get_settings.cache_clear()

    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10801)
    campaign = await _seed_campaign(db_session, owner, project)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_global_off",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "write_tool_disabled"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_disabled_specific_flag_rejected(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED", "false")
    get_settings.cache_clear()

    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10802)
    campaign = await _seed_campaign(db_session, owner, project)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_specific_off",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "write_tool_disabled"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_success_create_plan_draft(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10803)
    campaign = await _seed_campaign(db_session, owner, project)
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "plan"},
        metadata={},
    )
    assert run is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_ok",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    draft = _tool_data(result)["draft"]
    assert draft["campaign_id"] == str(campaign.id)
    assert draft["status"] == "draft"
    assert draft["draft_id"]
    assert draft["created_at"]

    row = await CampaignPlanDraftRepository(db_session).get_by_id_for_campaign(
        UUID(draft["draft_id"]),
        owner.id,
        project.id,
        campaign.id,
    )
    assert row is not None
    assert row.source_agent_run_id == run.id
    assert row.title == "June plan"


@pytest.mark.asyncio
async def test_archived_campaign_error_envelope(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10804)
    campaign = await _seed_campaign(db_session, owner, project)
    await MarketingCampaignService(db_session).archive(owner.id, project.id, campaign.id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_archived",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.INVALID_ARGUMENTS.value
    assert result.metadata["reason"] == "campaign_archived"


@pytest.mark.asyncio
async def test_secret_payload_error_envelope(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10805)
    campaign = await _seed_campaign(db_session, owner, project)
    run = await _seed_agent_run(db_session, owner, agent)
    payload = _sample_plan_payload()
    payload["api_key"] = "secret-value"

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_secret",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments={
                "project_id": str(project.id),
                "campaign_id": str(campaign.id),
                "title": "Bad plan",
                "plan_payload": payload,
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
    assert result.metadata["reason"] == "invalid_plan_payload"


@pytest.mark.asyncio
async def test_wrong_owner_project_error_envelope(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner_a, project_a, agent_a = await _seed_strategist_project(db_session, telegram_id=10806)
    campaign = await _seed_campaign(db_session, owner_a, project_a)
    owner_b = await UserRepository(db_session).create(UserTable(telegram_id=10807))
    project_b = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner_b.id, name="Other project"),
    )
    agent_b = await AgentService(db_session).create_agent(
        owner_b.id,
        AgentCreateRequest(project_id=project_b.id, type=AgentType.STRATEGIST),
    )
    assert agent_b is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_scope",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project_a.id, campaign_id=campaign.id),
        ),
        _context(owner_id=owner_b.id, project_id=project_b.id, agent_id=agent_b.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] in {
        ToolExecutionErrorCode.PERMISSION_DENIED.value,
        ToolExecutionErrorCode.NOT_FOUND.value,
    }


@pytest.mark.asyncio
async def test_project_id_mismatch_rejected(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10808)
    campaign = await _seed_campaign(db_session, owner, project)
    other_project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Second project"),
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_mismatch",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=other_project.id, campaign_id=campaign.id),
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "project_access_denied"


def test_source_agent_run_id_argument_rejected() -> None:
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
async def test_audit_log_written(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10809)
    campaign = await _seed_campaign(db_session, owner, project)
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "audit"},
        metadata={},
    )
    assert run is not None
    context = _context(
        owner_id=owner.id,
        project_id=project.id,
        agent_id=agent.id,
        agent_run_id=run.id,
    )
    tool_call = ToolCall(
        id="call_cp_audit",
        name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
        arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
    )
    audit_service = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit_service,
    )
    await executor.execute(tool_call, context)
    await db_session.commit()

    logs = await ToolExecutionLogRepository(db_session).list_by_run(owner.id, run.id)
    assert len(logs) == 1
    assert logs[0].execution_mode == "write"
    assert logs[0].tool_name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
    serialized = json.dumps(logs[0].arguments_preview)
    assert "source_agent_run_id" not in serialized


@pytest.mark.parametrize(
    "agent_type",
    [
        AgentType.COPYWRITER,
        AgentType.ANALYST,
        AgentType.RESEARCHER,
        AgentType.CRITIC,
    ],
)
def test_forbidden_agent_types_do_not_see_tool(
    agent_type: AgentType,
    enable_plan_draft_create: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME not in tools
    assert agent_type not in CAMPAIGN_PLAN_DRAFT_CREATE_ALLOWED_AGENT_TYPES


@pytest.mark.parametrize(
    "agent_type",
    [
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    ],
)
def test_allowed_agent_types_see_tool_when_enabled(
    agent_type: AgentType,
    enable_plan_draft_create: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME in tools


@pytest.mark.asyncio
async def test_forbidden_agent_type_call_rejected(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=10810))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Copywriter plan"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    campaign = await _seed_campaign(db_session, owner, project)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_copywriter",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.COPYWRITER,
        ),
    )
    assert result.status == "failed"
    assert result.output["error"]["code"] == ToolExecutionErrorCode.PERMISSION_DENIED.value
    assert result.metadata["reason"] == "tool_not_allowed_for_agent_type"


@pytest.mark.asyncio
async def test_tool_does_not_create_assets_or_jobs(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10811)
    campaign = await _seed_campaign(db_session, owner, project)
    run = await _seed_agent_run(db_session, owner, agent)
    assets_before = await ContentAssetRepository(db_session).list_by_project(
        owner.id,
        project.id,
    )
    jobs_before = await PublicationJobRepository(db_session).list_for_project(
        project.id,
        owner_id=owner.id,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_no_side",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments=_tool_arguments(project_id=project.id, campaign_id=campaign.id),
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"

    assets_after = await ContentAssetRepository(db_session).list_by_project(
        owner.id,
        project.id,
    )
    jobs_after = await PublicationJobRepository(db_session).list_for_project(
        project.id,
        owner_id=owner.id,
    )
    assert len(assets_after) == len(assets_before)
    assert len(jobs_after) == len(jobs_before)


@pytest.mark.asyncio
async def test_oversized_plan_payload_rejected(
    db_session: AsyncSession,
    enable_plan_draft_create: None,
) -> None:
    owner, project, agent = await _seed_strategist_project(db_session, telegram_id=10812)
    campaign = await _seed_campaign(db_session, owner, project)
    run = await _seed_agent_run(db_session, owner, agent)
    huge_items = [
        {
            "title": f"Item {index}",
            "channel": "telegram",
            "format": "text",
            "notes": "x" * 400,
        }
        for index in range(120)
    ]
    payload = {
        "goal": "Big plan",
        "target_audience": "All",
        "key_message": "Scale",
        "content_items": huge_items,
    }
    assert len(json.dumps(payload).encode("utf-8")) > PLAN_PAYLOAD_MAX_JSON_BYTES

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cp_big",
            name=CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
            arguments={
                "project_id": str(project.id),
                "campaign_id": str(campaign.id),
                "title": "Too big",
                "plan_payload": payload,
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
    assert result.metadata["reason"] == "invalid_plan_payload"
    listed = await CampaignPlanDraftRepository(db_session).list_by_campaign(
        owner.id,
        project.id,
        campaign.id,
    )
    assert listed == []


def test_write_tool_names_include_plan_draft_create() -> None:
    assert CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME in WRITE_TOOL_NAMES

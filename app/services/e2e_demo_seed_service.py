"""Deterministic E2E demo seed across frozen layers (Phase AI.80)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import DateTime, event, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.marketing_specialist_registry import get_marketing_specialist
from app.core.exceptions import InvalidStateError
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.publishing.contracts import PublishingChannelStatus
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)
from app.schemas.contracts import (
    AgentType,
    MarketingExecutionPlan,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistTask,
    MarketingSpecialistType,
    ScenarioWizardRunStatus,
    UserRole,
)
from app.schemas.crud import AgentCreateRequest, ProjectCreate, UserCreate
from app.publishing_foundation.contracts import PublishingFoundationChannelType
from app.schemas.publishing_foundation import PublishingFoundationChannelCreateRequest
from app.services.agents import AgentService
from app.services.auth import AuthService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService
from app.services.media_asset_service import MediaAssetService
from app.services.media_brief_service import MediaBriefService
from app.services.projects_service import ProjectService
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publication_package_service import PublicationPackageService
from app.services.publishing_foundation_channel_service import PublishingFoundationChannelService
from app.services.specialist_execution_service import SpecialistExecutionService
from app.services.users_service import UserService
from app.db.base import ensure_naive_utc
from app.db.repositories.user_repo import UserRepository

E2E_DEMO_TELEGRAM_ID = 9_000_200
E2E_DEMO_USER_EMAIL = "e2e-demo@botfazer.local"
E2E_DEMO_USER_NAME = "E2E Demo User"
E2E_DEMO_PROJECT_NAME = "E2E MVP Demo Project"
E2E_DEMO_PLAN_TITLE = "E2E MVP Demo Marketing Plan"
E2E_DEMO_V2_PLAN_TITLE = "E2E V2 Marketing Demo Plan"
E2E_DEMO_CHANNEL_NAME = "E2E Telegram Dry-Run"
E2E_DEMO_API_KEY_NAME = "E2E demo flow key"
E2E_DEMO_MARKER = "e2e_v1"


@contextmanager
def _postgres_naive_utc_writes(session: AsyncSession) -> Iterator[None]:
    """Normalize naive UTC timestamps for demo seed on PostgreSQL only."""
    import app.db.base as db_base

    sync_session = session.sync_session
    original_utc_now = db_base.utc_now
    db_base.utc_now = lambda: ensure_naive_utc(original_utc_now())

    def _normalize_naive_utc_before_flush(
        _session_obj: object,
        _flush_context: object,
        _instances: object,
    ) -> None:
        for obj in list(sync_session.new) + list(sync_session.dirty):
            state = inspect(obj)
            if state.mapper is None:
                continue
            for attr in state.mapper.column_attrs:
                column = attr.columns[0]
                if not isinstance(column.type, DateTime) or column.type.timezone:
                    continue
                value = getattr(obj, attr.key, None)
                if isinstance(value, datetime) and value.tzinfo is not None:
                    setattr(obj, attr.key, ensure_naive_utc(value))

    event.listen(sync_session, "before_flush", _normalize_naive_utc_before_flush)
    try:
        yield
    finally:
        event.remove(sync_session, "before_flush", _normalize_naive_utc_before_flush)
        db_base.utc_now = original_utc_now


_E2E_AGENT_TYPES: tuple[AgentType, ...] = (
    AgentType.ORCHESTRATOR,
    AgentType.RESEARCHER,
    AgentType.STRATEGIST,
    AgentType.COPYWRITER,
    AgentType.CONTENT_PLANNER,
)


@dataclass(frozen=True)
class E2eDemoSeedResult:
    user_id: UUID
    project_id: UUID
    marketing_plan_id: UUID
    execution_run_id: UUID
    copywriter_output_id: UUID
    content_asset_id: UUID
    media_brief_id: UUID
    media_asset_id: UUID
    publication_package_id: UUID
    foundation_channel_id: UUID
    publication_package_job_id: UUID
    api_key_plain: str | None
    scenario_plan_id: UUID | None = None
    wizard_run_id: UUID | None = None


def _demo_execution_plan() -> MarketingExecutionPlan:
    tasks: list[MarketingSpecialistTask] = []
    for specialist in MarketingPipelineExecutionService.pipeline_order():
        profile = get_marketing_specialist(specialist)
        tasks.append(
            MarketingSpecialistTask(
                specialist=specialist,
                objective=profile.default_objective,
                expected_output=profile.default_expected_output,
            ),
        )
    return MarketingExecutionPlan(
        goal="Demonstrate BotFazer marketing-to-publish pipeline in Telegram dry-run",
        project_context={"demo_seed": E2E_DEMO_MARKER, "channel": "telegram"},
        specialist_tasks=tasks,
    )


def _demo_v2_execution_plan() -> MarketingExecutionPlan:
    from app.agents.marketer.marketing_specialist_registry import V2_DEMO_EXECUTION_ORDER

    tasks: list[MarketingSpecialistTask] = []
    for specialist in V2_DEMO_EXECUTION_ORDER:
        profile = get_marketing_specialist(specialist)
        tasks.append(
            MarketingSpecialistTask(
                specialist=specialist,
                objective=profile.default_objective,
                expected_output=profile.default_expected_output,
            ),
        )
    return MarketingExecutionPlan(
        goal="Demonstrate BotFazer v2 marketing specialists (offer through ad creative)",
        project_context={"demo_seed": E2E_DEMO_MARKER, "track": "v2_marketing"},
        specialist_tasks=tasks,
    )


class E2eDemoSeedService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _normalize_legacy_postgres_demo_enums(self) -> None:
        """PG native-enum smoke runs stored StrEnum member names; ORM expects values."""
        from sqlalchemy import text

        tid = E2E_DEMO_TELEGRAM_ID
        columns = await self._session.execute(
            text(
                """
                SELECT c.table_name, c.column_name
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                  AND c.data_type = 'character varying'
                  AND EXISTS (
                      SELECT 1
                      FROM information_schema.columns o
                      WHERE o.table_schema = 'public'
                        AND o.table_name = c.table_name
                        AND o.column_name = 'owner_id'
                  )
                """,
            ),
        )
        for table_name, column_name in columns.all():
            await self._session.execute(
                text(
                    f'UPDATE "{table_name}" SET "{column_name}" = lower("{column_name}") '
                    "WHERE owner_id IN (SELECT id FROM users WHERE telegram_id = :tid) "
                    f'AND "{column_name}" ~ \'^[A-Z_]+$\'',
                ),
                {"tid": tid},
            )
        await self._session.execute(
            text(
                "UPDATE users SET role = lower(role), "
                "beta_access_status = lower(beta_access_status) "
                "WHERE telegram_id = :tid "
                "AND (role ~ '^[A-Z_]+$' OR beta_access_status ~ '^[A-Z_]+$')",
            ),
            {"tid": tid},
        )
        await self._session.execute(
            text(
                "UPDATE agents SET type = lower(type), status = lower(status) "
                "WHERE owner_id IN (SELECT id FROM users WHERE telegram_id = :tid) "
                "AND (type ~ '^[A-Z_]+$' OR status ~ '^[A-Z_]+$')",
            ),
            {"tid": tid},
        )
        await self._session.flush()

    async def _ensure_user(self) -> tuple[Any, UUID]:
        user_repo = UserRepository(self._session)
        user_service = UserService(self._session)
        user = await user_repo.get_by_telegram_id(E2E_DEMO_TELEGRAM_ID)
        if user is None:
            user = await user_service.create(
                UserCreate(
                    telegram_id=E2E_DEMO_TELEGRAM_ID,
                    email=E2E_DEMO_USER_EMAIL,
                    display_name=E2E_DEMO_USER_NAME,
                    role=UserRole.OWNER,
                    is_active=True,
                ),
            )
        return user, user.id

    async def _ensure_project(self, owner_id: UUID) -> Any:
        project_service = ProjectService(self._session)
        projects = await project_service.list(user_id=owner_id)
        project = next((p for p in projects if p.name == E2E_DEMO_PROJECT_NAME), None)
        if project is None:
            project = await project_service.create(
                ProjectCreate(
                    owner_id=owner_id,
                    name=E2E_DEMO_PROJECT_NAME,
                    description="End-to-end MVP demo across frozen marketing and publishing layers",
                ),
            )
        if project is None:
            raise RuntimeError("failed to create E2E demo project")
        return project

    async def _ensure_agents(self, owner_id: UUID, project_id: UUID) -> None:
        agent_service = AgentService(self._session)
        existing = await agent_service.list_agents(owner_id, project_id=project_id)
        for agent_type in _E2E_AGENT_TYPES:
            row = next((a for a in existing if a.type == agent_type), None)
            if row is None:
                row = await agent_service.create_agent(
                    owner_id,
                    AgentCreateRequest(project_id=project_id, type=agent_type),
                )
            if row is not None:
                await agent_service.activate_agent(row.id, owner_id)

    async def _find_demo_plan(self, owner_id: UUID, project_id: UUID) -> Any | None:
        plans = await MarketingPlanRepository(self._session).list_by_project(
            owner_id,
            project_id,
            limit=50,
        )
        if not plans:
            return None
        return next((p for p in plans if p.title == E2E_DEMO_PLAN_TITLE), None)

    async def seed(
        self,
        *,
        refresh_api_key: bool = False,
        owner_id: UUID | None = None,
        include_v2_marketing: bool = False,
        scenario: str | None = None,
        wizard: bool = False,
    ) -> E2eDemoSeedResult:
        from app.core.config import get_settings

        if get_settings().database_url.startswith("postgresql"):
            with _postgres_naive_utc_writes(self._session):
                return await self._seed_impl(
                    refresh_api_key=refresh_api_key,
                    owner_id=owner_id,
                    include_v2_marketing=include_v2_marketing,
                    scenario=scenario,
                    wizard=wizard,
                )
        return await self._seed_impl(
            refresh_api_key=refresh_api_key,
            owner_id=owner_id,
            include_v2_marketing=include_v2_marketing,
            scenario=scenario,
            wizard=wizard,
        )

    async def _seed_impl(
        self,
        *,
        refresh_api_key: bool = False,
        owner_id: UUID | None = None,
        include_v2_marketing: bool = False,
        scenario: str | None = None,
        wizard: bool = False,
    ) -> E2eDemoSeedResult:
        from app.core.config import get_settings

        if get_settings().database_url.startswith("postgresql"):
            await self._normalize_legacy_postgres_demo_enums()
        if owner_id is None:
            _user, owner_id = await self._ensure_user()
        else:
            user_row = await UserService(self._session).get_by_id(owner_id)
            if user_row is None:
                raise RuntimeError("owner_id not found for E2E seed")
        project = await self._ensure_project(owner_id)
        project_id = project.id
        await self._ensure_agents(owner_id, project_id)

        plan_service = MarketingPlanService(self._session)
        run_service = MarketingPlanExecutionService(self._session)
        specialist_exec = SpecialistExecutionService(self._session)
        output_service = MarketingSpecialistOutputService(self._session)
        asset_service = ContentAssetService(self._session)
        brief_service = MediaBriefService(self._session)
        media_asset_service = MediaAssetService(self._session)
        package_service = PublicationPackageService(self._session)
        channel_service = PublishingFoundationChannelService(self._session)
        job_service = PublicationPackageJobService(self._session)

        plan = await self._find_demo_plan(owner_id, project_id)
        if plan is None:
            plan = await plan_service.create_from_execution_plan(
                owner_id,
                project_id,
                _demo_execution_plan(),
                title=E2E_DEMO_PLAN_TITLE,
            )
        if plan is None:
            raise RuntimeError("failed to create E2E marketing plan")

        if plan.status != MarketingPlanStatus.APPROVED:
            plan = await plan_service.approve(owner_id, project_id, plan.id)
        if plan is None:
            raise InvalidStateError("failed to approve E2E marketing plan")

        runs = await MarketingPlanExecutionRunRepository(self._session).list_by_project(
            owner_id,
            project_id,
            marketing_plan_id=plan.id,
            limit=5,
        )
        run = runs[0] if runs else None
        if run is None:
            run = await run_service.create_from_approved_plan(owner_id, project_id, plan.id)
        if run is None:
            raise RuntimeError("failed to create E2E execution run")

        if run.status == MarketingPlanExecutionStatus.QUEUED:
            run = await run_service.start(owner_id, project_id, run.id)
        if run is None:
            raise RuntimeError("failed to start E2E execution run")

        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        for index, snapshot in enumerate(snapshots):
            if snapshot.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
                continue
            if snapshot.specialist not in MarketingPipelineExecutionService.pipeline_order():
                continue
            await specialist_exec.execute_task_specialist(
                owner_id,
                project_id,
                run.id,
                index,
            )
            run = await run_service.get(owner_id, project_id, run.id)
            if run is None:
                raise RuntimeError("execution run missing after specialist execute")

        if include_v2_marketing:
            await self._seed_v2_marketing_outputs(owner_id, project_id, plan_service, run_service, specialist_exec)

        scenario_plan_id: UUID | None = None
        wizard_run_id: UUID | None = None
        if scenario is not None and not wizard:
            scenario_plan = await plan_service.create_from_scenario(owner_id, project_id, scenario)
            if scenario_plan is None:
                raise RuntimeError(f"unknown or failed scenario: {scenario}")
            scenario_plan_id = scenario_plan.id

        if wizard:
            if scenario is None:
                raise RuntimeError("--wizard requires --scenario")
            from app.services.scenario_wizard_service import ScenarioWizardService

            wizard_service = ScenarioWizardService(self._session)
            wizard_run = await wizard_service.create_run(owner_id, project_id, scenario)
            if wizard_run is None:
                raise RuntimeError(f"failed to create wizard run for scenario: {scenario}")
            wizard_run = await wizard_service.advance_until_checkpoint(
                owner_id,
                project_id,
                wizard_run.id,
            )
            if wizard_run is None:
                raise RuntimeError("wizard run missing after checkpoint advance")
            if wizard_run.status != ScenarioWizardRunStatus.SUCCEEDED:
                reason = wizard_run.failure_reason or wizard_run.status.value
                raise RuntimeError(f"wizard seed failed at {wizard_run.current_step}: {reason}")
            wizard_run_id = wizard_run.id

        outputs = await MarketingSpecialistOutputRepository(self._session).list_by_project(
            owner_id,
            project_id,
            execution_run_id=run.id,
            specialist=MarketingSpecialistType.COPYWRITER,
            limit=5,
        )
        copywriter = outputs[0] if outputs else None
        if copywriter is None:
            raise RuntimeError("copywriter output missing after E2E seed specialists")

        if copywriter.status != MarketingSpecialistOutputStatus.APPROVED:
            copywriter = await output_service.approve(owner_id, project_id, copywriter.id)
        if copywriter is None:
            raise RuntimeError("failed to approve copywriter output")

        from app.db.repositories.content_assets import ContentAssetRepository

        asset_repo = ContentAssetRepository(self._session)
        asset = await asset_repo.get_by_source_specialist_output_id(
            owner_id,
            project_id,
            copywriter.id,
        )
        if asset is None:
            asset = await output_service.create_content_asset_from_copywriter(
                owner_id,
                project_id,
                copywriter.id,
            )
            if asset is None:
                raise RuntimeError("failed to create content asset from copywriter")
        if asset is None:
            raise RuntimeError("content asset missing")

        if asset.status == ContentAssetStatus.DRAFT:
            await asset_service.submit_for_review_asset(owner_id, project_id, asset.id)
            asset = await asset_repo.get_by_id_for_owner(asset.id, owner_id, project_id)
        if asset is not None and asset.status == ContentAssetStatus.REVIEW:
            asset = await asset_service.approve_asset(owner_id, project_id, asset.id)
        if asset is None or asset.status != ContentAssetStatus.APPROVED:
            raise RuntimeError("content asset not approved")

        from app.db.repositories.media_briefs import MediaBriefRepository

        brief_repo = MediaBriefRepository(self._session)
        briefs = await brief_repo.list_by_project(
            owner_id,
            project_id,
            content_asset_id=asset.id,
            limit=5,
        )
        brief = briefs[0] if briefs else None
        if brief is None:
            brief = await brief_service.create_from_approved_content_asset(
                owner_id,
                project_id,
                asset.id,
            )
        if brief is None:
            raise RuntimeError("failed to create media brief")

        if brief.status == MediaBriefStatus.DRAFT:
            await brief_service.submit_for_review(owner_id, project_id, brief.id)
            brief = await brief_repo.get_by_id_for_owner(brief.id, owner_id, project_id)
        if brief is not None and brief.status == MediaBriefStatus.REVIEW:
            brief = await brief_service.approve_brief(owner_id, project_id, brief.id)
        if brief is None or brief.status != MediaBriefStatus.APPROVED:
            raise RuntimeError("media brief not approved")

        from app.db.repositories.media_assets import MediaAssetRepository

        media_repo = MediaAssetRepository(self._session)
        media_rows = await media_repo.list_by_project(
            owner_id,
            project_id,
            media_brief_id=brief.id,
            limit=5,
        )
        media_asset = media_rows[0] if media_rows else None
        if media_asset is None:
            media_asset = await media_asset_service.create_placeholder_from_approved_brief(
                owner_id,
                project_id,
                brief.id,
                media_type="image",
            )
        if media_asset is None:
            raise RuntimeError("failed to create placeholder media asset")

        packages = await PublicationPackageRepository(self._session).list_by_project(
            owner_id,
            project_id,
            content_asset_id=asset.id,
            limit=5,
        )
        package = packages[0] if packages else None
        if package is None:
            package = await package_service.create_from_approved_asset(
                owner_id,
                project_id,
                asset.id,
                channel="telegram",
            )
        if package is None:
            raise RuntimeError("failed to create publication package")

        if package.status == PublicationPackageStatus.DRAFT:
            await package_service.submit_for_review(owner_id, project_id, package.id)
            package = await PublicationPackageRepository(self._session).get_by_id_for_owner(
                package.id,
                owner_id,
                project_id,
            )
        if package is not None and package.status == PublicationPackageStatus.REVIEW:
            package = await package_service.approve_package(owner_id, project_id, package.id)
        if package is None or package.status != PublicationPackageStatus.APPROVED:
            raise RuntimeError("publication package not approved")

        channels = await PublishingChannelRepository(self._session).list_for_project(
            project_id,
            owner_id=owner_id,
            include_archived=True,
        )
        channel = next((c for c in (channels or []) if c.name == E2E_DEMO_CHANNEL_NAME), None)
        if channel is None:
            channel_row = await channel_service.create(
                owner_id,
                project_id,
                PublishingFoundationChannelCreateRequest(
                    name=E2E_DEMO_CHANNEL_NAME,
                    channel_type=PublishingFoundationChannelType.TELEGRAM,
                    status="active",
                    config_metadata={"chat_id": "-1009876543210"},
                ),
            )
            if channel_row is None:
                raise RuntimeError("failed to create foundation channel")
            channel = await PublishingChannelRepository(self._session).get_for_owner(
                channel_row.id,
                owner_id=owner_id,
                project_id=project_id,
            )
        if channel is None or channel.status != PublishingChannelStatus.ACTIVE:
            raise RuntimeError("foundation channel not active")

        jobs = await PublicationPackageJobRepository(self._session).list_by_project(
            owner_id,
            project_id,
            publication_package_id=package.id,
            limit=5,
        )
        job = jobs[0] if jobs else None
        if job is None:
            job, _created = await job_service.create_from_approved_package(
                owner_id,
                project_id,
                package.id,
                channel.id,
            )
        if job is None:
            raise RuntimeError("failed to create publication package job")
        if job.status != PublicationPackageJobStatus.QUEUED:
            raise RuntimeError("E2E demo job must remain queued for scheduler demo")

        if job.schedule_status == PublicationPackageJobScheduleStatus.UNSCHEDULED:
            from app.services.publishing_schedule_service import PublishingScheduleService

            scheduled_for = datetime.now(UTC) + timedelta(hours=24)
            scheduled_job = await PublishingScheduleService(self._session).schedule_job(
                owner_id,
                project_id,
                job.id,
                scheduled_for=scheduled_for,
            )
            if scheduled_job is not None:
                job = scheduled_job

        plain_key: str | None = None
        auth = AuthService(self._session)
        existing_keys = await auth.list_api_keys(owner_id)
        active = next(
            (k for k in existing_keys if k.name == E2E_DEMO_API_KEY_NAME and k.revoked_at is None),
            None,
        )
        if active is None or refresh_api_key:
            if active is not None and refresh_api_key:
                await auth.revoke_api_key(active.id, owner_id)
            created_key = await auth.create_api_key(owner_id, E2E_DEMO_API_KEY_NAME)
            plain_key = created_key.plain_key

        return E2eDemoSeedResult(
            user_id=owner_id,
            project_id=project_id,
            marketing_plan_id=plan.id,
            execution_run_id=run.id,
            copywriter_output_id=copywriter.id,
            content_asset_id=asset.id,
            media_brief_id=brief.id,
            media_asset_id=media_asset.id,
            publication_package_id=package.id,
            foundation_channel_id=channel.id,
            publication_package_job_id=job.id,
            api_key_plain=plain_key,
            scenario_plan_id=scenario_plan_id,
            wizard_run_id=wizard_run_id,
        )

    async def _seed_v2_marketing_outputs(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_service: MarketingPlanService,
        run_service: MarketingPlanExecutionService,
        specialist_exec: SpecialistExecutionService,
    ) -> None:
        from app.agents.marketer.marketing_specialist_registry import V2_DEMO_EXECUTION_ORDER

        v2_plan = await self._find_demo_plan_by_title(owner_id, project_id, E2E_DEMO_V2_PLAN_TITLE)
        if v2_plan is None:
            v2_plan = await plan_service.create_from_execution_plan(
                owner_id,
                project_id,
                _demo_v2_execution_plan(),
                title=E2E_DEMO_V2_PLAN_TITLE,
            )
        if v2_plan is None:
            raise RuntimeError("failed to create E2E v2 marketing plan")
        if v2_plan.status != MarketingPlanStatus.APPROVED:
            v2_plan = await plan_service.approve(owner_id, project_id, v2_plan.id)
        if v2_plan is None:
            raise InvalidStateError("failed to approve E2E v2 marketing plan")

        v2_runs = await MarketingPlanExecutionRunRepository(self._session).list_by_project(
            owner_id,
            project_id,
            marketing_plan_id=v2_plan.id,
            limit=5,
        )
        v2_run = v2_runs[0] if v2_runs else None
        if v2_run is None:
            v2_run = await run_service.create_from_approved_plan(owner_id, project_id, v2_plan.id)
        if v2_run is None:
            raise RuntimeError("failed to create E2E v2 execution run")
        if v2_run.status == MarketingPlanExecutionStatus.QUEUED:
            v2_run = await run_service.start(owner_id, project_id, v2_run.id)
        if v2_run is None:
            raise RuntimeError("failed to start E2E v2 execution run")

        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(v2_run)
        for specialist in V2_DEMO_EXECUTION_ORDER:
            v2_run = await run_service.get(owner_id, project_id, v2_run.id)
            if v2_run is None:
                raise RuntimeError("v2 execution run missing")
            snapshots = MarketingPlanExecutionService.task_snapshots_for_row(v2_run)
            index = next(
                i for i, snap in enumerate(snapshots) if snap.specialist == specialist
            )
            if snapshots[index].status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
                continue
            await specialist_exec.execute_task_specialist(
                owner_id,
                project_id,
                v2_run.id,
                index,
            )

    async def _find_demo_plan_by_title(
        self,
        owner_id: UUID,
        project_id: UUID,
        title: str,
    ) -> Any | None:
        plans = await MarketingPlanRepository(self._session).list_by_project(
            owner_id,
            project_id,
            limit=50,
        )
        if not plans:
            return None
        return next((p for p in plans if p.title == title), None)

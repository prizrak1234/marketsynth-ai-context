"""Marketing plan persistence and approval gate (Phase AI.28)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.marketing_plan import MarketingPlanTable, MarketingPlanVersionTable
from app.db.repositories.marketing_plan_versions import MarketingPlanVersionRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.schemas.contracts import (
    MarketingExecutionMode,
    MarketingExecutionPlan,
    MarketingPlanStatus,
    MarketingSpecialistTask,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_TITLE_MAX = 512
_GOAL_MAX = 4096


def _truncate_title(goal: str) -> str:
    clean = sanitize_text(goal).strip()
    if len(clean) <= _TITLE_MAX:
        return clean or "Marketing plan"
    return clean[: _TITLE_MAX - 1].rstrip() + "…"


def _specialist_tasks_to_json(tasks: list[MarketingSpecialistTask]) -> list[dict[str, Any]]:
    return [task.model_dump(mode="json") for task in tasks]


def _specialist_tasks_from_json(raw: list[Any]) -> list[MarketingSpecialistTask]:
    parsed: list[MarketingSpecialistTask] = []
    for item in raw:
        if isinstance(item, dict):
            parsed.append(MarketingSpecialistTask.model_validate(item))
    return parsed


class MarketingPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plans = MarketingPlanRepository(session)
        self._versions = MarketingPlanVersionRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create_from_execution_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        execution_plan: MarketingExecutionPlan,
        *,
        title: str | None = None,
        source_run_id: UUID | None = None,
        source_session_id: UUID | None = None,
        source_scenario_id: str | None = None,
        source_scenario_name: str | None = None,
        created_by_run_id: UUID | None = None,
    ) -> MarketingPlanTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        from app.services.beta_limits_service import BetaLimitsService

        await BetaLimitsService(self._session).assert_can_create_marketing_plan(
            owner_id,
            project_id,
        )

        goal = sanitize_text(execution_plan.goal).strip()
        if not goal:
            raise InvalidStateError("Marketing execution plan goal is empty")

        tasks = execution_plan.specialist_tasks
        if not tasks:
            raise InvalidStateError("Marketing execution plan has no specialist tasks")

        plan_title = sanitize_text(title or _truncate_title(goal)).strip()[:_TITLE_MAX]
        tasks_json = _specialist_tasks_to_json(tasks)
        project_context = dict(execution_plan.project_context or {})

        async with transactional(self._session):
            plan_row = MarketingPlanTable(
                owner_id=owner_id,
                project_id=project_id,
                source_run_id=source_run_id,
                source_session_id=source_session_id,
                source_scenario_id=source_scenario_id,
                source_scenario_name=source_scenario_name,
                title=plan_title,
                goal=goal[:_GOAL_MAX],
                project_context=project_context or None,
                specialist_tasks=tasks_json,
                execution_mode=execution_plan.execution_mode,
                status=MarketingPlanStatus.DRAFT,
                current_version_number=1,
                approved_version_number=None,
            )
            plan_row = await self._plans.create(plan_row)

            version_row = MarketingPlanVersionTable(
                marketing_plan_id=plan_row.id,
                version_number=1,
                goal=plan_row.goal,
                project_context=plan_row.project_context,
                specialist_tasks=tasks_json,
                execution_mode=plan_row.execution_mode,
                created_by_run_id=created_by_run_id or source_run_id,
            )
            await self._versions.create(version_row)
            return plan_row

    async def create_from_scenario(
        self,
        owner_id: UUID,
        project_id: UUID,
        scenario_id: str,
    ) -> MarketingPlanTable | None:
        from app.marketing.scenarios import get_scenario

        template = get_scenario(scenario_id)
        if template is None:
            return None

        execution_plan = MarketingExecutionPlan(
            goal=template.goal,
            project_context={
                "scenario_id": template.id,
                "industry": template.industry,
            },
            specialist_tasks=list(template.default_plan_tasks),
        )
        return await self.create_from_execution_plan(
            owner_id,
            project_id,
            execution_plan,
            title=template.name,
            source_scenario_id=template.id,
            source_scenario_name=template.name,
        )

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
    ) -> MarketingPlanTable | None:
        return await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: MarketingPlanStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingPlanTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._plans.list_by_project(
            owner_id,
            project_id,
            status=status,
            limit=limit,
        )

    async def approve(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
    ) -> MarketingPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        if row.status == MarketingPlanStatus.ARCHIVED:
            raise InvalidStateError("Archived marketing plans cannot be approved")
        if row.status != MarketingPlanStatus.DRAFT:
            raise InvalidStateError("Only draft marketing plans can be approved")

        async with transactional(self._session):
            row.status = MarketingPlanStatus.APPROVED
            row.approved_version_number = row.current_version_number
            return await self._plans.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
    ) -> MarketingPlanTable | None:
        row = await self.get(owner_id, project_id, plan_id)
        if row is None:
            return None
        if row.status == MarketingPlanStatus.ARCHIVED:
            return row
        if row.status not in (
            MarketingPlanStatus.DRAFT,
            MarketingPlanStatus.APPROVED,
        ):
            raise InvalidStateError("Marketing plan cannot be archived from this status")

        async with transactional(self._session):
            row.status = MarketingPlanStatus.ARCHIVED
            return await self._plans.update(row)

    async def list_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
    ) -> list[MarketingPlanVersionTable] | None:
        plan = await self.get(owner_id, project_id, plan_id)
        if plan is None:
            return None
        return await self._versions.list_for_plan(plan.id)

    async def get_version(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
        version_number: int,
    ) -> MarketingPlanVersionTable | None:
        plan = await self.get(owner_id, project_id, plan_id)
        if plan is None:
            return None
        return await self._versions.get_version(plan.id, version_number)

    @staticmethod
    def specialist_tasks_for_row(row: MarketingPlanTable) -> list[MarketingSpecialistTask]:
        return _specialist_tasks_from_json(list(row.specialist_tasks or []))

    @staticmethod
    def specialist_tasks_for_version(
        row: MarketingPlanVersionTable,
    ) -> list[MarketingSpecialistTask]:
        return _specialist_tasks_from_json(list(row.specialist_tasks or []))

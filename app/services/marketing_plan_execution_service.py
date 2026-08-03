"""Marketing plan execution run skeleton (Phase AI.29) — no specialists, tools, or LLM."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.repositories.marketing_plan_execution_runs import (
    MarketingPlanExecutionRunRepository,
)
from app.db.repositories.marketing_plan_versions import MarketingPlanVersionRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.schemas.contracts import (
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskSnapshot,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistTask,
)
from app.services.marketing_pipeline_execution_service import (
    MarketingPipelineExecutionService,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_TERMINAL_STATUSES = frozenset(
    {
        MarketingPlanExecutionStatus.SUCCEEDED,
        MarketingPlanExecutionStatus.FAILED,
        MarketingPlanExecutionStatus.CANCELLED,
    },
)

_PLACEHOLDER_MESSAGE = "Specialist execution is not enabled in this phase"
_SAFE_ERROR_MAX = 500


def _tasks_from_version(specialist_tasks: list[Any]) -> list[MarketingPlanExecutionTaskSnapshot]:
    snapshots: list[MarketingPlanExecutionTaskSnapshot] = []
    for item in specialist_tasks:
        if not isinstance(item, dict):
            continue
        try:
            task = MarketingSpecialistTask.model_validate(item)
        except Exception:
            continue
        snapshots.append(
            MarketingPlanExecutionTaskSnapshot(
                specialist=task.specialist,
                objective=task.objective,
                expected_output=task.expected_output,
                status=MarketingPlanExecutionTaskStatus.PENDING,
            ),
        )
    return snapshots


def _snapshots_to_json(
    snapshots: list[MarketingPlanExecutionTaskSnapshot],
) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in snapshots]


def _snapshots_from_json(raw: list[Any]) -> list[MarketingPlanExecutionTaskSnapshot]:
    parsed: list[MarketingPlanExecutionTaskSnapshot] = []
    for item in raw:
        if isinstance(item, dict):
            parsed.append(MarketingPlanExecutionTaskSnapshot.model_validate(item))
    return parsed


def _ensure_not_terminal(row: MarketingPlanExecutionRunTable) -> None:
    if row.status in _TERMINAL_STATUSES:
        raise InvalidStateError(f"Execution run is already {row.status.value}")


class MarketingPlanExecutionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = MarketingPlanExecutionRunRepository(session)
        self._plans = MarketingPlanRepository(session)
        self._versions = MarketingPlanVersionRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create_from_approved_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        plan_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        plan = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
        if plan is None:
            return None
        if plan.status != MarketingPlanStatus.APPROVED:
            raise InvalidStateError("Only approved marketing plans can start execution runs")
        if plan.approved_version_number is None:
            raise InvalidStateError("Marketing plan has no approved version")

        version = await self._versions.get_version(plan.id, plan.approved_version_number)
        if version is None:
            raise InvalidStateError("Approved marketing plan version not found")

        snapshots = _tasks_from_version(list(version.specialist_tasks or []))
        if not snapshots:
            raise InvalidStateError("Approved plan version has no specialist tasks")

        async with transactional(self._session):
            row = MarketingPlanExecutionRunTable(
                owner_id=owner_id,
                project_id=project_id,
                marketing_plan_id=plan.id,
                marketing_plan_version_number=plan.approved_version_number,
                status=MarketingPlanExecutionStatus.QUEUED,
                task_snapshots=_snapshots_to_json(snapshots),
                result_summary=None,
                error=None,
            )
            return await self._runs.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        return await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        marketing_plan_id: UUID | None = None,
        status: MarketingPlanExecutionStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingPlanExecutionRunTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._runs.list_by_project(
            owner_id,
            project_id,
            marketing_plan_id=marketing_plan_id,
            status=status,
            limit=limit,
        )

    async def start(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        _ensure_not_terminal(row)
        if row.status != MarketingPlanExecutionStatus.QUEUED:
            raise InvalidStateError("Execution run can only start from queued status")

        async with transactional(self._session):
            row.status = MarketingPlanExecutionStatus.RUNNING
            row.started_at = utc_now()
            return await self._runs.update(row)

    async def complete_placeholder(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        _ensure_not_terminal(row)
        if row.status != MarketingPlanExecutionStatus.RUNNING:
            raise InvalidStateError(
                "Placeholder completion is only allowed from running status",
            )

        snapshots = _snapshots_from_json(list(row.task_snapshots or []))
        completed = [
            item.model_copy(
                update={"status": MarketingPlanExecutionTaskStatus.PLACEHOLDER_COMPLETED},
            )
            for item in snapshots
        ]
        now = utc_now()
        summary = {
            "mode": "placeholder",
            "message": _PLACEHOLDER_MESSAGE,
            "task_count": len(completed),
        }

        async with transactional(self._session):
            row.status = MarketingPlanExecutionStatus.SUCCEEDED
            row.task_snapshots = _snapshots_to_json(completed)
            row.result_summary = summary
            row.error = None
            row.finished_at = now
            return await self._runs.update(row)

    async def fail(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        safe_error: str,
    ) -> MarketingPlanExecutionRunTable | None:
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        _ensure_not_terminal(row)
        if row.status not in (
            MarketingPlanExecutionStatus.QUEUED,
            MarketingPlanExecutionStatus.RUNNING,
        ):
            raise InvalidStateError("Execution run cannot fail from this status")

        safe_message = sanitize_text(safe_error).strip()[:_SAFE_ERROR_MAX] or "Execution failed"
        now = utc_now()

        async with transactional(self._session):
            row.status = MarketingPlanExecutionStatus.FAILED
            row.error = {"message": safe_message}
            row.finished_at = now
            return await self._runs.update(row)

    async def cancel(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        _ensure_not_terminal(row)
        if row.status not in (
            MarketingPlanExecutionStatus.QUEUED,
            MarketingPlanExecutionStatus.RUNNING,
        ):
            raise InvalidStateError("Execution run can only be cancelled from queued or running")

        now = utc_now()
        async with transactional(self._session):
            row.status = MarketingPlanExecutionStatus.CANCELLED
            row.finished_at = now
            return await self._runs.update(row)

    @staticmethod
    def task_snapshots_for_row(
        row: MarketingPlanExecutionRunTable,
    ) -> list[MarketingPlanExecutionTaskSnapshot]:
        return _snapshots_from_json(list(row.task_snapshots or []))

    async def complete_if_all_tasks_completed(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> tuple[MarketingPlanExecutionRunTable | None, bool]:
        """Mark run succeeded when every task snapshot is specialist_completed (AI.38)."""
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None, False
        updated, completed = self._apply_completion_if_ready(row)
        if not completed:
            return row, False
        async with transactional(self._session):
            return await self._runs.update(updated), True

    @staticmethod
    def _apply_completion_if_ready(
        row: MarketingPlanExecutionRunTable,
    ) -> tuple[MarketingPlanExecutionRunTable, bool]:
        if row.status != MarketingPlanExecutionStatus.RUNNING:
            return row, False
        snapshots = _snapshots_from_json(list(row.task_snapshots or []))
        if not MarketingPipelineExecutionService.all_tasks_specialist_completed(snapshots):
            return row, False
        row.status = MarketingPlanExecutionStatus.SUCCEEDED
        row.finished_at = utc_now()
        row.result_summary = (
            MarketingPipelineExecutionService.build_specialist_pipeline_result_summary(
                snapshots,
            )
        )
        row.error = None
        return row, True

"""Marketing specialist task execution (Phase AI.31+) — uses pipeline validation (AI.37)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.specialists.executor import execute_marketing_specialist
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.repositories.marketing_plan_execution_runs import (
    MarketingPlanExecutionRunRepository,
)
from app.db.repositories.marketing_plan_versions import MarketingPlanVersionRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_output_versions import (
    MarketingSpecialistOutputVersionRepository,
)
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.schemas.contracts import (
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskSnapshot,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistExecutionInput,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_pipeline_execution_service import (
    MarketingPipelineExecutionService,
    V2_EXECUTION_ENABLED_SPECIALISTS,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_ACTIVE_OUTPUT_STATUSES = frozenset(
    {
        MarketingSpecialistOutputStatus.DRAFT,
        MarketingSpecialistOutputStatus.APPROVED,
    },
)
_ENABLED_SPECIALISTS = (
    frozenset(MarketingPipelineExecutionService.pipeline_order()) | V2_EXECUTION_ENABLED_SPECIALISTS
)
_SAFE_NOTES_MAX = 500


@dataclass(frozen=True)
class SpecialistTaskExecutionResult:
    specialist_output_id: UUID
    specialist: MarketingSpecialistType
    status: MarketingSpecialistOutputStatus
    safe_summary: str
    execution_run_status: MarketingPlanExecutionStatus
    run_completed: bool


def _snapshots_to_json(
    snapshots: list[MarketingPlanExecutionTaskSnapshot],
) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in snapshots]


class SpecialistExecutionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = MarketingPlanExecutionRunRepository(session)
        self._outputs = MarketingSpecialistOutputRepository(session)
        self._output_versions = MarketingSpecialistOutputVersionRepository(session)
        self._plans = MarketingPlanRepository(session)
        self._versions = MarketingPlanVersionRepository(session)
        self._projects = ProjectService(session)
        self._pipeline = MarketingPipelineExecutionService()

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _default_safe_summary(specialist: MarketingSpecialistType) -> str:
        if specialist == MarketingSpecialistType.RESEARCHER:
            return "Desk research ready for review."
        if specialist == MarketingSpecialistType.CONTENT_PLANNER:
            return "Content plan ready for review."
        if specialist == MarketingSpecialistType.COPYWRITER:
            return "Content copy ready for review."
        if specialist == MarketingSpecialistType.CRITIC:
            return "Content critique ready for review."
        if specialist == MarketingSpecialistType.ANALYST:
            return "Execution analysis ready for review."
        if specialist == MarketingSpecialistType.OFFER_STRATEGIST:
            return "Offer strategy ready for review."
        if specialist == MarketingSpecialistType.FUNNEL_ARCHITECT:
            return "Funnel design ready for review."
        if specialist == MarketingSpecialistType.LEAD_MAGNET_SPECIALIST:
            return "Lead magnet concept ready for review."
        if specialist == MarketingSpecialistType.SALES_COPYWRITER:
            return "Sales copy ready for review."
        if specialist == MarketingSpecialistType.EMAIL_DM_SPECIALIST:
            return "Email/DM sequence ready for review."
        if specialist == MarketingSpecialistType.CRO_SPECIALIST:
            return "CRO recommendations ready for review."
        if specialist == MarketingSpecialistType.SMM_STRATEGIST:
            return "SMM strategy ready for review."
        if specialist == MarketingSpecialistType.AD_CREATIVE_STRATEGIST:
            return "Ad creative strategy ready for review."
        return "Strategic direction ready for review."

    async def execute_task_specialist(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        task_index: int,
    ) -> SpecialistTaskExecutionResult | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        run = await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)
        if run is None:
            return None

        if run.status != MarketingPlanExecutionStatus.RUNNING:
            raise InvalidStateError("Specialist execution requires a running execution run")

        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        if task_index < 0 or task_index >= len(snapshots):
            raise InvalidStateError("Task index is out of range for this execution run")

        snapshot = snapshots[task_index]
        if snapshot.specialist not in _ENABLED_SPECIALISTS:
            raise InvalidStateError(
                "Specialist execution is not enabled for this role yet",
            )

        existing = await self._outputs.get_by_run_and_task_index(run.id, task_index)
        if existing is not None and existing.status in _ACTIVE_OUTPUT_STATUSES:
            raise InvalidStateError(
                "A specialist output already exists for this task",
            )

        run_outputs = await self._outputs.list_by_project(
            owner_id,
            project_id,
            execution_run_id=run.id,
            limit=100,
        )

        validation = self._pipeline.validate_task_execution(
            specialist=snapshot.specialist,
            task_index=task_index,
            snapshots=snapshots,
            run_outputs=run_outputs,
        )
        if not validation.can_execute:
            raise InvalidStateError(
                validation.safe_error or "Specialist dependencies are not satisfied",
            )

        plan = await self._plans.get_by_id_for_owner(run.marketing_plan_id, owner_id, project_id)
        if plan is None:
            raise InvalidStateError("Marketing plan not found for execution run")
        if plan.status != MarketingPlanStatus.APPROVED:
            raise InvalidStateError("Marketing plan must remain approved")
        if plan.approved_version_number is None:
            raise InvalidStateError("Marketing plan has no approved version")
        if run.marketing_plan_version_number != plan.approved_version_number:
            raise InvalidStateError(
                "Execution run plan version does not match the approved plan version",
            )

        version = await self._versions.get_version(plan.id, run.marketing_plan_version_number)
        if version is None:
            raise InvalidStateError("Approved marketing plan version not found")

        project_context: dict[str, Any] | None = None
        if isinstance(version.project_context, dict):
            project_context = dict(version.project_context)

        execution_input = MarketingSpecialistExecutionInput(
            execution_run_id=run.id,
            task_index=task_index,
            marketing_plan_id=plan.id,
            marketing_plan_version_number=run.marketing_plan_version_number,
            specialist=snapshot.specialist,
            objective=snapshot.objective,
            expected_output=snapshot.expected_output,
            plan_goal=version.goal,
            project_context=project_context,
            prior_outputs=list(validation.prior_outputs),
        )

        execution_output = await execute_marketing_specialist(execution_input)
        safe_summary = sanitize_text(execution_output.safe_summary).strip()[:_SAFE_NOTES_MAX]
        if not safe_summary:
            safe_summary = self._default_safe_summary(snapshot.specialist)
        safe_notes = safe_summary

        run_completed = False
        async with transactional(self._session):
            output_row = MarketingSpecialistOutputTable(
                owner_id=owner_id,
                project_id=project_id,
                marketing_plan_id=plan.id,
                execution_run_id=run.id,
                task_index=task_index,
                specialist=snapshot.specialist,
                title=execution_output.title,
                output_type=execution_output.output_type,
                content=execution_output.content,
                structured_data=dict(execution_output.structured_data),
                status=MarketingSpecialistOutputStatus.DRAFT,
                current_version_number=1,
                approved_version_number=None,
            )
            output_row = await self._outputs.create(output_row)

            version_row = MarketingSpecialistOutputVersionTable(
                specialist_output_id=output_row.id,
                version_number=1,
                title=output_row.title,
                output_type=output_row.output_type,
                content=output_row.content,
                structured_data=output_row.structured_data,
                created_by_run_id=run.id,
            )
            await self._output_versions.create(version_row)

            updated_snapshot = snapshot.model_copy(
                update={
                    "status": MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
                    "output_ref": str(output_row.id),
                    "safe_notes": safe_notes,
                },
            )
            snapshots[task_index] = updated_snapshot
            run.task_snapshots = _snapshots_to_json(snapshots)
            run = await self._runs.update(run)
            run, run_completed = MarketingPlanExecutionService._apply_completion_if_ready(run)
            if run_completed:
                run = await self._runs.update(run)

            return SpecialistTaskExecutionResult(
                specialist_output_id=output_row.id,
                specialist=snapshot.specialist,
                status=MarketingSpecialistOutputStatus.DRAFT,
                safe_summary=safe_summary,
                execution_run_status=MarketingPlanExecutionStatus(run.status),
                run_completed=run_completed,
            )

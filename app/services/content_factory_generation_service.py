"""Content Factory copywriter material generation — composes frozen specialist pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.content_factory.brief_to_execution_plan import brief_to_execution_plan
from app.content_factory.provider_gate import assess_content_factory_provider_readiness
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.marketing import ContentAssetTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import (
    ContentFactoryBriefInput,
    ContentFactoryGeneratedAssetLineage,
    ContentFactoryGenerateMaterialsResponse,
    ContentFactoryGenerationStage,
    ContentFactoryGenerationStep,
    ContentFactoryProviderReadiness,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService
from app.services.projects_service import ProjectService
from app.services.specialist_execution_service import SpecialistExecutionService

_MIN_ASSETS = 3
_PIPELINE_SPECIALISTS = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.COPYWRITER,
)


@dataclass(frozen=True)
class _RunContext:
    marketing_plan_id: UUID
    execution_run_id: UUID
    content_planner_output_id: UUID | None = None
    copywriter_output_id: UUID | None = None
    brief_channel: str | None = None


class ContentFactoryGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._plans = MarketingPlanService(session)
        self._execution = MarketingPlanExecutionService(session)
        self._specialists = SpecialistExecutionService(session)
        self._outputs = MarketingSpecialistOutputService(session)
        self._runs = MarketingPlanExecutionRunRepository(session)
        self._output_rows = MarketingSpecialistOutputRepository(session)
        self._assets = ContentAssetRepository(session)

    async def provider_readiness(self) -> ContentFactoryProviderReadiness:
        return assess_content_factory_provider_readiness()

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _find_assets_by_idempotency(
        self,
        owner_id: UUID,
        project_id: UUID,
        idempotency_key: str,
    ) -> list[ContentAssetTable]:
        rows = await self._assets.list_by_project(owner_id, project_id, limit=500)
        matched = [
            row
            for row in rows
            if row.status != ContentAssetStatus.ARCHIVED
            and (row.asset_metadata or {}).get("content_factory_generation") is True
            and (row.asset_metadata or {}).get("content_factory_idempotency_key") == idempotency_key
        ]
        return matched

    def _lineage_from_assets(
        self,
        assets: list[ContentAssetTable],
    ) -> list[ContentFactoryGeneratedAssetLineage]:
        lineage: list[ContentFactoryGeneratedAssetLineage] = []
        for asset in assets:
            metadata = asset.asset_metadata or {}
            slot = metadata.get("content_slot") or metadata.get("content_item_index") or 0
            planner_raw = metadata.get("source_content_planner_output_id")
            if not asset.source_marketing_plan_id or not asset.source_execution_run_id:
                continue
            if not asset.source_specialist_output_id or not planner_raw:
                continue
            lineage.append(
                ContentFactoryGeneratedAssetLineage(
                    content_asset_id=asset.id,
                    content_slot=int(slot),
                    title=asset.title,
                    status=asset.status.value
                    if hasattr(asset.status, "value")
                    else str(asset.status),
                    source_marketing_plan_id=asset.source_marketing_plan_id,
                    source_execution_run_id=asset.source_execution_run_id,
                    source_content_planner_output_id=UUID(str(planner_raw)),
                    source_copywriter_output_id=asset.source_specialist_output_id,
                    llm_provider=str(metadata.get("llm_provider")) if metadata.get("llm_provider") else None,
                    llm_model=str(metadata.get("llm_model")) if metadata.get("llm_model") else None,
                ),
            )
        return lineage

    def _completed_response(
        self,
        *,
        ctx: _RunContext,
        assets: list[ContentAssetTable],
        safe_message: str,
    ) -> ContentFactoryGenerateMaterialsResponse:
        return ContentFactoryGenerateMaterialsResponse(
            stage=ContentFactoryGenerationStage.COMPLETED,
            safe_message=safe_message,
            marketing_plan_id=ctx.marketing_plan_id,
            execution_run_id=ctx.execution_run_id,
            content_planner_output_id=ctx.content_planner_output_id,
            copywriter_output_id=ctx.copywriter_output_id,
            content_assets=self._lineage_from_assets(assets),
        )

    async def _task_index_for(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        specialist: MarketingSpecialistType,
    ) -> int:
        run = await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)
        if run is None:
            raise InvalidStateError("Execution run not found")
        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        for index, snapshot in enumerate(snapshots):
            if snapshot.specialist == specialist:
                return index
        raise InvalidStateError(f"Specialist task not found: {specialist.value}")

    async def _execute_specialist(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        specialist: MarketingSpecialistType,
    ) -> None:
        index = await self._task_index_for(owner_id, project_id, run_id, specialist)
        run = await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)
        if run is None:
            raise InvalidStateError("Execution run not found")
        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
        if snapshots[index].status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
            return
        await self._specialists.execute_task_specialist(owner_id, project_id, run_id, index)

    async def _output_for_specialist(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        specialist: MarketingSpecialistType,
    ):
        outputs = await self._output_rows.list_by_project(
            owner_id,
            project_id,
            execution_run_id=run_id,
            specialist=specialist,
            limit=5,
        )
        if not outputs:
            raise InvalidStateError(f"Missing specialist output: {specialist.value}")
        return outputs[0]

    async def _prepare_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief: ContentFactoryBriefInput,
    ) -> _RunContext:
        execution_plan = brief_to_execution_plan(brief)
        plan = await self._plans.create_from_execution_plan(
            owner_id,
            project_id,
            execution_plan,
            title=brief.topic[:512],
        )
        if plan is None:
            raise InvalidStateError("Failed to create marketing plan")

        approved = await self._plans.approve(owner_id, project_id, plan.id)
        if approved is None:
            raise InvalidStateError("Failed to approve marketing plan")

        created_run = await self._execution.create_from_approved_plan(
            owner_id,
            project_id,
            plan.id,
        )
        if created_run is None:
            raise InvalidStateError("Failed to create execution run")
        started = await self._execution.start(owner_id, project_id, created_run.id)
        if started is None:
            raise InvalidStateError("Failed to start execution run")

        for specialist in _PIPELINE_SPECIALISTS[:3]:
            await self._execute_specialist(owner_id, project_id, started.id, specialist)

        planner = await self._output_for_specialist(
            owner_id,
            project_id,
            started.id,
            MarketingSpecialistType.CONTENT_PLANNER,
        )
        return _RunContext(
            marketing_plan_id=plan.id,
            execution_run_id=started.id,
            content_planner_output_id=planner.id,
            brief_channel=sanitize_text(brief.channel).strip().lower() or None,
        )

    async def _run_copywriter(
        self,
        owner_id: UUID,
        project_id: UUID,
        ctx: _RunContext,
    ) -> _RunContext:
        await self._execute_specialist(
            owner_id,
            project_id,
            ctx.execution_run_id,
            MarketingSpecialistType.COPYWRITER,
        )
        copywriter = await self._output_for_specialist(
            owner_id,
            project_id,
            ctx.execution_run_id,
            MarketingSpecialistType.COPYWRITER,
        )
        return _RunContext(
            marketing_plan_id=ctx.marketing_plan_id,
            execution_run_id=ctx.execution_run_id,
            content_planner_output_id=ctx.content_planner_output_id,
            copywriter_output_id=copywriter.id,
            brief_channel=ctx.brief_channel,
        )

    async def _finalize_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        ctx: _RunContext,
        *,
        idempotency_key: str | None,
    ) -> list[ContentAssetTable]:
        if ctx.copywriter_output_id is None or ctx.content_planner_output_id is None:
            raise InvalidStateError("Copywriter pipeline context is incomplete")

        copywriter = await self._outputs.get(owner_id, project_id, ctx.copywriter_output_id)
        if copywriter is None:
            raise InvalidStateError("Copywriter output not found")

        if copywriter.status == MarketingSpecialistOutputStatus.DRAFT:
            copywriter = await self._outputs.approve(
                owner_id,
                project_id,
                ctx.copywriter_output_id,
            )
        if copywriter is None:
            raise InvalidStateError("Failed to approve copywriter output")

        assets = await self._outputs.create_content_assets_from_copywriter(
            owner_id,
            project_id,
            ctx.copywriter_output_id,
            content_planner_output_id=ctx.content_planner_output_id,
            idempotency_key=idempotency_key,
            minimum_assets=_MIN_ASSETS,
            expected_channel=ctx.brief_channel,
        )
        await self._execution.complete_if_all_tasks_completed(
            owner_id,
            project_id,
            ctx.execution_run_id,
        )
        return assets

    async def get_generation_status(
        self,
        owner_id: UUID,
        project_id: UUID,
        execution_run_id: UUID,
    ) -> ContentFactoryGenerateMaterialsResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        run = await self._runs.get_by_id_for_owner(execution_run_id, owner_id, project_id)
        if run is None:
            return None

        ctx = _RunContext(
            marketing_plan_id=run.marketing_plan_id,
            execution_run_id=run.id,
        )
        try:
            planner = await self._output_for_specialist(
                owner_id,
                project_id,
                run.id,
                MarketingSpecialistType.CONTENT_PLANNER,
            )
            ctx = _RunContext(
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
                content_planner_output_id=planner.id,
            )
        except InvalidStateError:
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.PREPARING_CONTENT_PLAN,
                safe_message="Готовим контент-план",
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
            )

        try:
            copywriter = await self._output_for_specialist(
                owner_id,
                project_id,
                run.id,
                MarketingSpecialistType.COPYWRITER,
            )
            ctx = _RunContext(
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
                content_planner_output_id=ctx.content_planner_output_id,
                copywriter_output_id=copywriter.id,
            )
        except InvalidStateError:
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.HANDING_TO_COPYWRITER,
                safe_message="Передаём задачу копирайтеру",
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
                content_planner_output_id=ctx.content_planner_output_id,
            )

        assets = await self._assets.list_by_source_specialist_output_id(
            owner_id,
            project_id,
            copywriter.id,
        )
        if len(assets) >= _MIN_ASSETS:
            return self._completed_response(
                ctx=ctx,
                assets=assets,
                safe_message="Черновики готовы к проверке",
            )
        if copywriter.status == MarketingSpecialistOutputStatus.DRAFT:
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.FORMING_MATERIALS,
                safe_message="Формируем материалы",
                marketing_plan_id=run.marketing_plan_id,
                execution_run_id=run.id,
                content_planner_output_id=ctx.content_planner_output_id,
                copywriter_output_id=copywriter.id,
            )

        return ContentFactoryGenerateMaterialsResponse(
            stage=ContentFactoryGenerationStage.VERIFYING_RESULT,
            safe_message="Проверяем результат",
            marketing_plan_id=run.marketing_plan_id,
            execution_run_id=run.id,
            content_planner_output_id=ctx.content_planner_output_id,
            copywriter_output_id=copywriter.id,
        )

    async def generate_materials(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        brief: ContentFactoryBriefInput,
        execution_run_id: UUID | None = None,
        step: ContentFactoryGenerationStep = ContentFactoryGenerationStep.ALL,
        idempotency_key: str | None = None,
    ) -> ContentFactoryGenerateMaterialsResponse:
        if not await self._ensure_project_owned(owner_id, project_id):
            raise InvalidStateError("Project not found")

        readiness = await self.provider_readiness()
        if not readiness.ready:
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.BLOCKED,
                safe_message=readiness.blocked_message_ru or "Генерация материалов временно недоступна",
                blocked_reason=readiness.blocked_reason,
            )

        resolved_key = idempotency_key or brief.idempotency_key
        if resolved_key:
            existing_assets = await self._find_assets_by_idempotency(
                owner_id,
                project_id,
                resolved_key,
            )
            if len(existing_assets) >= _MIN_ASSETS:
                sample = existing_assets[0]
                ctx = _RunContext(
                    marketing_plan_id=sample.source_marketing_plan_id,
                    execution_run_id=sample.source_execution_run_id,
                    content_planner_output_id=UUID(
                        str((sample.asset_metadata or {}).get("source_content_planner_output_id")),
                    )
                    if (sample.asset_metadata or {}).get("source_content_planner_output_id")
                    else None,
                    copywriter_output_id=sample.source_specialist_output_id,
                )
                return self._completed_response(
                    ctx=ctx,
                    assets=existing_assets,
                    safe_message="Черновики готовы к проверке",
                )

        if step == ContentFactoryGenerationStep.ALL:
            ctx = await self._prepare_plan(owner_id, project_id, brief)
            ctx = await self._run_copywriter(owner_id, project_id, ctx)
            try:
                assets = await self._finalize_assets(
                    owner_id,
                    project_id,
                    ctx,
                    idempotency_key=resolved_key,
                )
            except InvalidStateError as exc:
                return ContentFactoryGenerateMaterialsResponse(
                    stage=ContentFactoryGenerationStage.FAILED,
                    safe_message=str(exc),
                    marketing_plan_id=ctx.marketing_plan_id,
                    execution_run_id=ctx.execution_run_id,
                    content_planner_output_id=ctx.content_planner_output_id,
                    copywriter_output_id=ctx.copywriter_output_id,
                )
            return self._completed_response(
                ctx=ctx,
                assets=assets,
                safe_message="Черновики готовы к проверке",
            )

        if step == ContentFactoryGenerationStep.PREPARE_PLAN:
            ctx = await self._prepare_plan(owner_id, project_id, brief)
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.HANDING_TO_COPYWRITER,
                safe_message="Передаём задачу копирайтеру",
                marketing_plan_id=ctx.marketing_plan_id,
                execution_run_id=ctx.execution_run_id,
                content_planner_output_id=ctx.content_planner_output_id,
            )

        if execution_run_id is None:
            raise InvalidStateError("execution_run_id is required for this generation step")

        run = await self._runs.get_by_id_for_owner(execution_run_id, owner_id, project_id)
        if run is None:
            raise InvalidStateError("Execution run not found")

        planner = await self._output_for_specialist(
            owner_id,
            project_id,
            run.id,
            MarketingSpecialistType.CONTENT_PLANNER,
        )
        ctx = _RunContext(
            marketing_plan_id=run.marketing_plan_id,
            execution_run_id=run.id,
            content_planner_output_id=planner.id,
        )

        if step == ContentFactoryGenerationStep.COPYWRITER:
            ctx = await self._run_copywriter(owner_id, project_id, ctx)
            return ContentFactoryGenerateMaterialsResponse(
                stage=ContentFactoryGenerationStage.FORMING_MATERIALS,
                safe_message="Формируем материалы",
                marketing_plan_id=ctx.marketing_plan_id,
                execution_run_id=ctx.execution_run_id,
                content_planner_output_id=ctx.content_planner_output_id,
                copywriter_output_id=ctx.copywriter_output_id,
            )

        if step == ContentFactoryGenerationStep.FINALIZE:
            try:
                copywriter = await self._output_for_specialist(
                    owner_id,
                    project_id,
                    run.id,
                    MarketingSpecialistType.COPYWRITER,
                )
                ctx = _RunContext(
                    marketing_plan_id=run.marketing_plan_id,
                    execution_run_id=run.id,
                    content_planner_output_id=planner.id,
                    copywriter_output_id=copywriter.id,
                )
            except InvalidStateError:
                ctx = await self._run_copywriter(owner_id, project_id, ctx)
            try:
                assets = await self._finalize_assets(
                    owner_id,
                    project_id,
                    ctx,
                    idempotency_key=resolved_key,
                )
            except InvalidStateError as exc:
                return ContentFactoryGenerateMaterialsResponse(
                    stage=ContentFactoryGenerationStage.FAILED,
                    safe_message=str(exc),
                    marketing_plan_id=ctx.marketing_plan_id,
                    execution_run_id=ctx.execution_run_id,
                    content_planner_output_id=ctx.content_planner_output_id,
                    copywriter_output_id=ctx.copywriter_output_id,
                )
            return self._completed_response(
                ctx=ctx,
                assets=assets,
                safe_message="Черновики готовы к проверке",
            )

        raise InvalidStateError(f"Unsupported generation step: {step.value}")

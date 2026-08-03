"""Scenario wizard run service — manual step engine (Phase AI.138–AI.141)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.scenario_wizard_run import ScenarioWizardRunTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.db.repositories.scenario_wizard_runs import ScenarioWizardRunRepository
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.marketing.scenario_wizard_content import create_content_asset_from_wizard_output
from app.marketing.scenario_wizard_steps import (
    SCENARIO_WIZARD_FIRST_STEP,
    SCENARIO_WIZARD_LAST_STEP,
    SCENARIO_WIZARD_STEPS,
    next_wizard_step,
)
from app.marketing.scenarios import get_scenario
from app.publishing.contracts import PublishingChannelStatus
from app.publishing_foundation.contracts import (
    PublicationPackageJobStatus,
    PublishingFoundationChannelType,
)
from app.schemas.contracts import (
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
    ScenarioWizardRunStatus,
)
from app.schemas.publishing_foundation import PublishingFoundationChannelCreateRequest
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService
from app.services.media_brief_service import MediaBriefService
from app.services.projects_service import ProjectService
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publication_package_service import PublicationPackageService
from app.services.publishing_foundation_channel_service import PublishingFoundationChannelService
from app.services.specialist_execution_service import SpecialistExecutionService
from app.services.transaction import transactional

_TERMINAL_STATUSES = frozenset(
    {
        ScenarioWizardRunStatus.SUCCEEDED,
        ScenarioWizardRunStatus.FAILED,
        ScenarioWizardRunStatus.CANCELLED,
    },
)
_WIZARD_CHANNEL_NAME = "Scenario Wizard Telegram Dry-Run"
_FAILURE_MAX = 1024
_CONTENT_SPECIALISTS = (
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.SALES_COPYWRITER,
)


def _parse_uuid(raw: Any) -> UUID | None:
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


class ScenarioWizardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = ScenarioWizardRunRepository(session)
        self._projects = ProjectService(session)
        self._plans = MarketingPlanRepository(session)
        self._plan_service = MarketingPlanService(session)
        self._execution_runs = MarketingPlanExecutionRunRepository(session)
        self._execution_service = MarketingPlanExecutionService(session)
        self._specialist_exec = SpecialistExecutionService(session)
        self._outputs = MarketingSpecialistOutputRepository(session)
        self._output_service = MarketingSpecialistOutputService(session)
        self._assets = ContentAssetRepository(session)
        self._asset_service = ContentAssetService(session)
        self._briefs = MediaBriefRepository(session)
        self._brief_service = MediaBriefService(session)
        self._packages = PublicationPackageRepository(session)
        self._package_service = PublicationPackageService(session)
        self._jobs = PublicationPackageJobRepository(session)
        self._job_service = PublicationPackageJobService(session)
        self._channels = PublishingChannelRepository(session)
        self._channel_service = PublishingFoundationChannelService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def step_results_for_row(row: ScenarioWizardRunTable) -> dict[str, Any]:
        return dict(row.step_results or {})

    async def create_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        scenario_id: str,
        *,
        source_campaign_id: UUID | None = None,
    ) -> ScenarioWizardRunTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        template = get_scenario(scenario_id)
        if template is None:
            return None

        if source_campaign_id is not None:
            from app.db.repositories.campaigns import CampaignRepository
            from app.schemas.contracts import CampaignStatus

            campaign = await CampaignRepository(self._session).get_by_id_for_owner(
                source_campaign_id,
                owner_id,
                project_id,
            )
            if campaign is None:
                raise InvalidStateError("Source campaign not found")
            if campaign.status == CampaignStatus.ARCHIVED:
                raise InvalidStateError("Cannot start wizard from archived campaign")
            if campaign.scenario_id and campaign.scenario_id != scenario_id:
                raise InvalidStateError("Scenario does not match campaign scenario_id")

        row = ScenarioWizardRunTable(
            owner_id=owner_id,
            project_id=project_id,
            scenario_id=template.id,
            scenario_name=template.name,
            source_campaign_id=source_campaign_id,
            status=ScenarioWizardRunStatus.DRAFT,
            current_step=SCENARIO_WIZARD_FIRST_STEP,
            step_results={},
            failure_reason=None,
            finished_at=None,
        )
        async with transactional(self._session):
            return await self._runs.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> ScenarioWizardRunTable | None:
        return await self._runs.get_by_id_for_owner(run_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: ScenarioWizardRunStatus | None = None,
        limit: int = 50,
    ) -> list[ScenarioWizardRunTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._runs.list_by_project(
            owner_id,
            project_id,
            status=status,
            limit=limit,
        )

    async def advance(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
    ) -> ScenarioWizardRunTable | None:
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        if row.status in _TERMINAL_STATUSES:
            raise InvalidStateError(f"Wizard run is already {row.status.value}")
        if row.status == ScenarioWizardRunStatus.PAUSED:
            row.status = ScenarioWizardRunStatus.RUNNING

        if row.status == ScenarioWizardRunStatus.DRAFT:
            row.status = ScenarioWizardRunStatus.RUNNING

        async with transactional(self._session):
            try:
                step_result = await self._execute_step(owner_id, project_id, row)
            except InvalidStateError as exc:
                row.status = ScenarioWizardRunStatus.FAILED
                row.failure_reason = sanitize_text(str(exc)).strip()[:_FAILURE_MAX]
                row.finished_at = utc_now()
                return await self._runs.update(row)

            results = dict(row.step_results or {})
            results.update(step_result)
            completed = list(results.get("steps_completed") or [])
            if row.current_step not in completed:
                completed.append(row.current_step)
            results["steps_completed"] = completed
            row.step_results = results
            row.failure_reason = None

            if row.current_step == SCENARIO_WIZARD_LAST_STEP:
                row.status = ScenarioWizardRunStatus.SUCCEEDED
                row.finished_at = utc_now()
            else:
                next_step = next_wizard_step(row.current_step)
                if next_step is None:
                    raise InvalidStateError(f"Unknown wizard step: {row.current_step}")
                row.current_step = next_step
                row.status = ScenarioWizardRunStatus.RUNNING

            return await self._runs.update(row)

    async def advance_until_checkpoint(
        self,
        owner_id: UUID,
        project_id: UUID,
        run_id: UUID,
        *,
        max_steps: int | None = None,
    ) -> ScenarioWizardRunTable | None:
        limit = max_steps if max_steps is not None else len(SCENARIO_WIZARD_STEPS)
        row = await self.get(owner_id, project_id, run_id)
        if row is None:
            return None
        for _ in range(limit):
            if row.status in _TERMINAL_STATUSES:
                break
            row = await self.advance(owner_id, project_id, run_id)
            if row is None:
                return None
        return row

    def _resolve_content_specialist(
        self,
        specialists: list[MarketingSpecialistType],
    ) -> MarketingSpecialistType:
        for candidate in _CONTENT_SPECIALISTS:
            if candidate in specialists:
                return candidate
        raise InvalidStateError(
            "Scenario plan has no copywriter or sales_copywriter for content asset steps",
        )

    async def _execute_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
    ) -> dict[str, Any]:
        step = row.current_step
        results = dict(row.step_results or {})
        handlers = {
            "create_plan": self._step_create_plan,
            "approve_plan": self._step_approve_plan,
            "create_execution_run": self._step_create_execution_run,
            "execute_specialists": self._step_execute_specialists,
            "approve_copywriter_output": self._step_approve_content_output,
            "create_content_asset": self._step_create_content_asset,
            "submit_asset": self._step_submit_asset,
            "approve_asset": self._step_approve_asset,
            "create_media_brief": self._step_create_media_brief,
            "submit_media_brief": self._step_submit_media_brief,
            "approve_media_brief": self._step_approve_media_brief,
            "create_publication_package": self._step_create_publication_package,
            "submit_package": self._step_submit_package,
            "approve_package": self._step_approve_package,
            "create_dry_run_job": self._step_create_dry_run_job,
        }
        handler = handlers.get(step)
        if handler is None:
            raise InvalidStateError(f"Unsupported wizard step: {step}")
        return await handler(owner_id, project_id, row, results)

    async def _step_create_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        plan_id = _parse_uuid(results.get("marketing_plan_id"))
        if plan_id is not None:
            existing = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
            if existing is not None:
                return {"marketing_plan_id": str(existing.id)}

        plan = await self._plan_service.create_from_scenario(
            owner_id,
            project_id,
            row.scenario_id,
        )
        if plan is None:
            raise InvalidStateError("Failed to create marketing plan from scenario")

        context = dict(plan.project_context or {})
        context["wizard_run_id"] = str(row.id)
        if row.source_campaign_id is not None:
            from app.services.campaign_brief_service import CampaignBriefService
            from app.services.campaign_layer_service import CampaignLayerService
            from app.services.campaign_skill_context_service import CampaignSkillContextService

            context = CampaignLayerService.tag_context(context, row.source_campaign_id)
            brief_summary = await CampaignBriefService(self._session).safe_summary_for_campaign(
                owner_id,
                project_id,
                row.source_campaign_id,
            )
            if brief_summary:
                context["campaign_brief_summary"] = brief_summary
            campaign = await CampaignLayerService(self._session).get(
                owner_id,
                project_id,
                row.source_campaign_id,
            )
            if campaign is not None:
                skill_context = CampaignSkillContextService.skill_context_from_campaign(campaign)
                skill_summaries = CampaignSkillContextService.safe_summaries_for_plan(skill_context)
                if skill_summaries:
                    context["campaign_skill_summaries"] = skill_summaries
        plan.project_context = context
        plan = await self._plans.update(plan)
        return {"marketing_plan_id": str(plan.id)}

    async def _step_approve_plan(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        plan_id = _parse_uuid(results.get("marketing_plan_id"))
        if plan_id is None:
            raise InvalidStateError("Wizard is missing marketing_plan_id")
        plan = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
        if plan is None:
            raise InvalidStateError("Marketing plan not found for wizard")
        if plan.status == MarketingPlanStatus.APPROVED:
            return {"marketing_plan_id": str(plan.id), "plan_status": plan.status.value}
        if plan.status != MarketingPlanStatus.DRAFT:
            raise InvalidStateError("Only draft marketing plans can be approved in wizard")

        approved = await self._plan_service.approve(owner_id, project_id, plan_id)
        if approved is None:
            raise InvalidStateError("Failed to approve marketing plan")
        return {
            "marketing_plan_id": str(approved.id),
            "plan_status": approved.status.value,
        }

    async def _step_create_execution_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        plan_id = _parse_uuid(results.get("marketing_plan_id"))
        if plan_id is None:
            raise InvalidStateError("Wizard is missing marketing_plan_id")

        run_id = _parse_uuid(results.get("execution_run_id"))
        if run_id is not None:
            existing = await self._execution_runs.get_by_id_for_owner(
                run_id,
                owner_id,
                project_id,
            )
            if existing is not None:
                if existing.status == MarketingPlanExecutionStatus.QUEUED:
                    started = await self._execution_service.start(owner_id, project_id, existing.id)
                    if started is None:
                        raise InvalidStateError("Failed to start execution run")
                    existing = started
                return {"execution_run_id": str(existing.id)}

        created = await self._execution_service.create_from_approved_plan(
            owner_id,
            project_id,
            plan_id,
        )
        if created is None:
            raise InvalidStateError("Failed to create execution run")
        started = await self._execution_service.start(owner_id, project_id, created.id)
        if started is None:
            raise InvalidStateError("Failed to start execution run")
        return {"execution_run_id": str(started.id)}

    async def _step_execute_specialists(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = _parse_uuid(results.get("execution_run_id"))
        if run_id is None:
            raise InvalidStateError("Wizard is missing execution_run_id")

        execution_run = await self._execution_runs.get_by_id_for_owner(
            run_id,
            owner_id,
            project_id,
        )
        if execution_run is None:
            raise InvalidStateError("Execution run not found for wizard")

        if execution_run.status == MarketingPlanExecutionStatus.QUEUED:
            execution_run = await self._execution_service.start(owner_id, project_id, run_id)
        if execution_run is None:
            raise InvalidStateError("Execution run must be running for specialist execution")
        if execution_run.status != MarketingPlanExecutionStatus.RUNNING:
            if execution_run.status == MarketingPlanExecutionStatus.SUCCEEDED:
                return {"execution_run_id": str(execution_run.id), "execution_status": "succeeded"}
            raise InvalidStateError("Execution run is not running")

        snapshots = MarketingPlanExecutionService.task_snapshots_for_row(execution_run)
        for index, snapshot in enumerate(snapshots):
            if snapshot.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
                continue
            await self._specialist_exec.execute_task_specialist(
                owner_id,
                project_id,
                run_id,
                index,
            )
            execution_run = await self._execution_runs.get_by_id_for_owner(
                run_id,
                owner_id,
                project_id,
            )
            if execution_run is None:
                raise InvalidStateError("Execution run missing after specialist execute")

        await self._execution_service.complete_if_all_tasks_completed(
            owner_id,
            project_id,
            run_id,
        )
        execution_run = await self._execution_runs.get_by_id_for_owner(
            run_id,
            owner_id,
            project_id,
        )
        if execution_run is None:
            raise InvalidStateError("Execution run missing after specialists")
        return {
            "execution_run_id": str(execution_run.id),
            "execution_status": execution_run.status.value,
        }

    async def _find_content_output(
        self,
        owner_id: UUID,
        project_id: UUID,
        results: dict[str, Any],
    ):
        run_id = _parse_uuid(results.get("execution_run_id"))
        plan_id = _parse_uuid(results.get("marketing_plan_id"))
        if run_id is None or plan_id is None:
            raise InvalidStateError("Wizard is missing execution context")

        plan = await self._plans.get_by_id_for_owner(plan_id, owner_id, project_id)
        if plan is None:
            raise InvalidStateError("Marketing plan not found")
        tasks = MarketingPlanService.specialist_tasks_for_row(plan)
        content_specialist = self._resolve_content_specialist([task.specialist for task in tasks])

        output_id = _parse_uuid(results.get("content_output_id"))
        if output_id is not None:
            existing = await self._outputs.get_by_id_for_owner(output_id, owner_id, project_id)
            if existing is not None:
                return existing, content_specialist

        outputs = await self._outputs.list_by_project(
            owner_id,
            project_id,
            execution_run_id=run_id,
            specialist=content_specialist,
            limit=5,
        )
        if not outputs:
            raise InvalidStateError("Content specialist output not found after execution")
        return outputs[0], content_specialist

    async def _step_approve_content_output(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        output, content_specialist = await self._find_content_output(owner_id, project_id, results)
        if output.status == MarketingSpecialistOutputStatus.APPROVED:
            return {
                "content_output_id": str(output.id),
                "content_specialist": content_specialist.value,
            }
        if output.status != MarketingSpecialistOutputStatus.DRAFT:
            raise InvalidStateError("Content output must be draft before approval")

        approved = await self._output_service.approve(owner_id, project_id, output.id)
        if approved is None:
            raise InvalidStateError("Failed to approve content specialist output")
        return {
            "content_output_id": str(approved.id),
            "content_specialist": content_specialist.value,
        }

    async def _step_create_content_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        asset_id = _parse_uuid(results.get("content_asset_id"))
        if asset_id is not None:
            existing = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
            if existing is not None:
                return {"content_asset_id": str(existing.id)}

        output, content_specialist = await self._find_content_output(owner_id, project_id, results)
        if output.status != MarketingSpecialistOutputStatus.APPROVED:
            raise InvalidStateError("Content output must be approved before asset creation")

        plan_id = _parse_uuid(results.get("marketing_plan_id"))
        run_id = _parse_uuid(results.get("execution_run_id"))
        if run_id is None:
            raise InvalidStateError("Wizard is missing execution_run_id")

        if content_specialist == MarketingSpecialistType.COPYWRITER:
            asset = await self._output_service.create_content_asset_from_copywriter(
                owner_id,
                project_id,
                output.id,
            )
        else:
            asset = await create_content_asset_from_wizard_output(
                self._session,
                owner_id,
                project_id,
                output_id=output.id,
                specialist=content_specialist,
                status=output.status.value,
                output_type=output.output_type,
                title=output.title,
                content=output.content,
                structured_data=dict(output.structured_data) if output.structured_data else None,
                marketing_plan_id=plan_id,
                execution_run_id=run_id,
                wizard_run_id=row.id,
            )
        if asset is None:
            raise InvalidStateError("Failed to create content asset")

        metadata = dict(asset.asset_metadata or {})
        metadata["wizard_run_id"] = str(row.id)
        if row.source_campaign_id is not None:
            from app.services.campaign_layer_service import CampaignLayerService

            metadata = CampaignLayerService.tag_context(metadata, row.source_campaign_id)
        asset.asset_metadata = metadata
        asset = await self._assets.update(asset)
        return {"content_asset_id": str(asset.id)}

    async def _step_submit_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        asset_id = _parse_uuid(results.get("content_asset_id"))
        if asset_id is None:
            raise InvalidStateError("Wizard is missing content_asset_id")
        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            raise InvalidStateError("Content asset not found")
        if asset.status == ContentAssetStatus.REVIEW:
            return {"content_asset_id": str(asset.id), "asset_status": asset.status.value}
        if asset.status != ContentAssetStatus.DRAFT:
            raise InvalidStateError("Only draft content assets can be submitted for review")

        await self._asset_service.submit_for_review_asset(owner_id, project_id, asset_id)
        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            raise InvalidStateError("Content asset missing after submit")
        return {"content_asset_id": str(asset.id), "asset_status": asset.status.value}

    async def _step_approve_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        asset_id = _parse_uuid(results.get("content_asset_id"))
        if asset_id is None:
            raise InvalidStateError("Wizard is missing content_asset_id")
        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            raise InvalidStateError("Content asset not found")
        if asset.status == ContentAssetStatus.APPROVED:
            return {"content_asset_id": str(asset.id), "asset_status": asset.status.value}
        if asset.status != ContentAssetStatus.REVIEW:
            raise InvalidStateError("Content asset must be in review before approval")

        approved = await self._asset_service.approve_asset(owner_id, project_id, asset_id)
        if approved is None:
            raise InvalidStateError("Failed to approve content asset")
        return {"content_asset_id": str(approved.id), "asset_status": approved.status.value}

    async def _step_create_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        brief_id = _parse_uuid(results.get("media_brief_id"))
        if brief_id is not None:
            existing = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
            if existing is not None:
                return {"media_brief_id": str(existing.id)}

        asset_id = _parse_uuid(results.get("content_asset_id"))
        if asset_id is None:
            raise InvalidStateError("Wizard is missing content_asset_id")
        brief = await self._brief_service.create_from_approved_content_asset(
            owner_id,
            project_id,
            asset_id,
        )
        if brief is None:
            raise InvalidStateError("Failed to create media brief")
        return {"media_brief_id": str(brief.id)}

    async def _step_submit_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        brief_id = _parse_uuid(results.get("media_brief_id"))
        if brief_id is None:
            raise InvalidStateError("Wizard is missing media_brief_id")
        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            raise InvalidStateError("Media brief not found")
        if brief.status == MediaBriefStatus.REVIEW:
            return {"media_brief_id": str(brief.id), "media_brief_status": brief.status.value}
        if brief.status != MediaBriefStatus.DRAFT:
            raise InvalidStateError("Only draft media briefs can be submitted")

        await self._brief_service.submit_for_review(owner_id, project_id, brief_id)
        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            raise InvalidStateError("Media brief missing after submit")
        return {"media_brief_id": str(brief.id), "media_brief_status": brief.status.value}

    async def _step_approve_media_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        brief_id = _parse_uuid(results.get("media_brief_id"))
        if brief_id is None:
            raise InvalidStateError("Wizard is missing media_brief_id")
        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            raise InvalidStateError("Media brief not found")
        if brief.status == MediaBriefStatus.APPROVED:
            return {"media_brief_id": str(brief.id), "media_brief_status": brief.status.value}
        if brief.status != MediaBriefStatus.REVIEW:
            raise InvalidStateError("Media brief must be in review before approval")

        approved = await self._brief_service.approve_brief(owner_id, project_id, brief_id)
        if approved is None:
            raise InvalidStateError("Failed to approve media brief")
        return {"media_brief_id": str(approved.id), "media_brief_status": approved.status.value}

    async def _step_create_publication_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        package_id = _parse_uuid(results.get("publication_package_id"))
        if package_id is not None:
            existing = await self._packages.get_by_id_for_owner(
                package_id,
                owner_id,
                project_id,
            )
            if existing is not None:
                return {"publication_package_id": str(existing.id)}

        asset_id = _parse_uuid(results.get("content_asset_id"))
        if asset_id is None:
            raise InvalidStateError("Wizard is missing content_asset_id")
        package = await self._package_service.create_from_approved_asset(
            owner_id,
            project_id,
            asset_id,
            channel="telegram",
        )
        if package is None:
            raise InvalidStateError("Failed to create publication package")
        return {"publication_package_id": str(package.id)}

    async def _step_submit_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        package_id = _parse_uuid(results.get("publication_package_id"))
        if package_id is None:
            raise InvalidStateError("Wizard is missing publication_package_id")
        package = await self._packages.get_by_id_for_owner(package_id, owner_id, project_id)
        if package is None:
            raise InvalidStateError("Publication package not found")
        if package.status == PublicationPackageStatus.REVIEW:
            return {
                "publication_package_id": str(package.id),
                "package_status": package.status.value,
            }
        if package.status != PublicationPackageStatus.DRAFT:
            raise InvalidStateError("Only draft publication packages can be submitted")

        await self._package_service.submit_for_review(owner_id, project_id, package_id)
        package = await self._packages.get_by_id_for_owner(package_id, owner_id, project_id)
        if package is None:
            raise InvalidStateError("Publication package missing after submit")
        return {
            "publication_package_id": str(package.id),
            "package_status": package.status.value,
        }

    async def _step_approve_package(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        package_id = _parse_uuid(results.get("publication_package_id"))
        if package_id is None:
            raise InvalidStateError("Wizard is missing publication_package_id")
        package = await self._packages.get_by_id_for_owner(package_id, owner_id, project_id)
        if package is None:
            raise InvalidStateError("Publication package not found")
        if package.status == PublicationPackageStatus.APPROVED:
            return {
                "publication_package_id": str(package.id),
                "package_status": package.status.value,
            }
        if package.status != PublicationPackageStatus.REVIEW:
            raise InvalidStateError("Publication package must be in review before approval")

        approved = await self._package_service.approve_package(owner_id, project_id, package_id)
        if approved is None:
            raise InvalidStateError("Failed to approve publication package")
        return {
            "publication_package_id": str(approved.id),
            "package_status": approved.status.value,
        }

    async def _ensure_wizard_channel(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> UUID:
        channels = await self._channels.list_for_project(
            project_id,
            owner_id=owner_id,
            include_archived=True,
        )
        channel = next(
            (item for item in (channels or []) if item.name == _WIZARD_CHANNEL_NAME),
            None,
        )
        if channel is not None and channel.status == PublishingChannelStatus.ACTIVE:
            return channel.id

        created = await self._channel_service.create(
            owner_id,
            project_id,
            PublishingFoundationChannelCreateRequest(
                name=_WIZARD_CHANNEL_NAME,
                channel_type=PublishingFoundationChannelType.TELEGRAM,
                status="active",
                config_metadata={"chat_id": "-100111222333", "wizard_dry_run": True},
            ),
        )
        if created is None:
            raise InvalidStateError("Failed to create wizard dry-run channel")
        return created.id

    async def _step_create_dry_run_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        row: ScenarioWizardRunTable,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        job_id = _parse_uuid(results.get("publication_package_job_id"))
        if job_id is not None:
            existing = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
            if existing is not None:
                if existing.status != PublicationPackageJobStatus.QUEUED:
                    raise InvalidStateError("Wizard dry-run job must remain queued")
                return {
                    "publication_package_job_id": str(existing.id),
                    "job_status": existing.status.value,
                }

        package_id = _parse_uuid(results.get("publication_package_id"))
        if package_id is None:
            raise InvalidStateError("Wizard is missing publication_package_id")
        channel_id = await self._ensure_wizard_channel(owner_id, project_id)

        jobs = await self._jobs.list_by_project(
            owner_id,
            project_id,
            publication_package_id=package_id,
            limit=5,
        )
        if jobs:
            job = jobs[0]
        else:
            job, _created = await self._job_service.create_from_approved_package(
                owner_id,
                project_id,
                package_id,
                channel_id,
            )
        if job is None:
            raise InvalidStateError("Failed to create dry-run publication job")
        if job.status != PublicationPackageJobStatus.QUEUED:
            raise InvalidStateError("Wizard dry-run job must remain queued — no real publish")

        return {
            "publication_package_job_id": str(job.id),
            "foundation_channel_id": str(channel_id),
            "job_status": job.status.value,
            "wizard_run_id": str(row.id),
        }

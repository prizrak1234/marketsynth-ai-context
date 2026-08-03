"""Campaign control center — timeline, health, next action (Phase AI.157–AI.163)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mappers import campaign_to_contract, marketing_skill_run_to_contract
from app.core.security import sanitize_text
from app.domain.campaign_skill_suggestion_engine import (
    CampaignSkillSuggestionInput,
    build_campaign_skill_suggestions,
)
from app.domain.marketing_tool_recommendations import build_tool_suggestions
from app.services.campaign_skill_context_service import CampaignSkillContextService
from app.db.models.campaign import CampaignTable
from app.db.models.marketing_plan import MarketingPlanTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.models.scenario_wizard_run import ScenarioWizardRunTable
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.marketing.scenario_wizard_steps import SCENARIO_WIZARD_STEPS
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)
from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    CampaignControlCenter,
    CampaignControlCenterSummary,
    CampaignFailureRecoveryHint,
    CampaignHealth,
    CampaignHealthStatus,
    CampaignMetrics,
    CampaignNextAction,
    CampaignNextActionType,
    CampaignResourceIds,
    CampaignStatus,
    CampaignSkillSuggestion,
    CampaignTimelineEvent,
    CampaignTimelineEventType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSkillRunStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
    ScenarioWizardRunStatus,
)
from app.services.campaign_layer_service import CampaignLayerService, campaign_id_in_context
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService
from app.services.projects_service import ProjectService

_PIPELINE = MarketingPipelineExecutionService.pipeline_order()
_CONTENT_SPECIALISTS = (
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_TERMINAL_WIZARD = frozenset(
    {
        ScenarioWizardRunStatus.SUCCEEDED,
        ScenarioWizardRunStatus.FAILED,
        ScenarioWizardRunStatus.CANCELLED,
    },
)
_WIZARD_STEP_COUNT = len(SCENARIO_WIZARD_STEPS)


@dataclass
class CampaignArtifacts:
    campaign: CampaignTable
    wizards: list[ScenarioWizardRunTable] = field(default_factory=list)
    latest_wizard: ScenarioWizardRunTable | None = None
    plans: list[MarketingPlanTable] = field(default_factory=list)
    latest_plan: MarketingPlanTable | None = None
    runs: list[MarketingPlanExecutionRunTable] = field(default_factory=list)
    latest_run: MarketingPlanExecutionRunTable | None = None
    outputs: list[Any] = field(default_factory=list)
    content_outputs: list[Any] = field(default_factory=list)
    assets: list[Any] = field(default_factory=list)
    latest_asset: Any | None = None
    briefs: list[Any] = field(default_factory=list)
    latest_brief: Any | None = None
    media_assets: list[Any] = field(default_factory=list)
    packages: list[Any] = field(default_factory=list)
    latest_package: Any | None = None
    jobs: list[Any] = field(default_factory=list)
    latest_job: Any | None = None
    skill_runs: list[Any] = field(default_factory=list)
    metrics: CampaignMetrics | None = None


class CampaignControlCenterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._layer = CampaignLayerService(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _load_artifacts(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignArtifacts | None:
        campaign = await self._layer.get(owner_id, project_id, campaign_id)
        if campaign is None:
            return None

        metrics = await self._layer.compute_metrics(owner_id, project_id, campaign_id)
        if metrics is None:
            return None

        plans = await self._layer._plans.list_by_project(owner_id, project_id, limit=200)
        linked_plans = [
            plan for plan in plans if campaign_id_in_context(plan.project_context, campaign_id)
        ]
        linked_plan_ids = {plan.id for plan in linked_plans}

        runs = await self._layer._runs.list_by_project(owner_id, project_id, limit=200)
        linked_runs = [run for run in runs if run.marketing_plan_id in linked_plan_ids]

        outputs = await self._layer._outputs.list_by_project(owner_id, project_id, limit=500)
        linked_outputs = [
            output for output in outputs if output.execution_run_id in {run.id for run in linked_runs}
        ]
        content_outputs = [
            output
            for output in linked_outputs
            if output.specialist in _CONTENT_SPECIALISTS
        ]

        assets = await self._layer._assets.list_by_project(owner_id, project_id, limit=500)
        linked_assets = [
            asset
            for asset in assets
            if campaign_id_in_context(asset.asset_metadata, campaign_id)
            or asset.source_marketing_plan_id in linked_plan_ids
        ]
        linked_asset_ids = {asset.id for asset in linked_assets}

        briefs = await self._layer._briefs.list_by_project(owner_id, project_id, limit=500)
        linked_briefs = [brief for brief in briefs if brief.content_asset_id in linked_asset_ids]

        media_rows = await self._layer._media_assets.list_by_project(owner_id, project_id, limit=500)
        linked_media = [media for media in media_rows if media.media_brief_id in {b.id for b in linked_briefs}]

        packages = await self._layer._packages.list_by_project(owner_id, project_id, limit=500)
        linked_packages = [
            package for package in packages if package.content_asset_id in linked_asset_ids
        ]
        linked_package_ids = {package.id for package in linked_packages}

        jobs = await self._layer._jobs.list_by_project(owner_id, project_id, limit=500)
        linked_jobs = [job for job in jobs if job.publication_package_id in linked_package_ids]

        wizards = await self._layer._wizards.list_by_project(owner_id, project_id, limit=100)
        linked_wizards = [wizard for wizard in wizards if wizard.source_campaign_id == campaign_id]

        from app.db.repositories.marketing_skill_runs import MarketingSkillRunRepository

        skill_runs = await MarketingSkillRunRepository(self._session).list_for_project(
            owner_id,
            project_id,
            campaign_id=campaign_id,
            limit=20,
        )

        latest_wizard = linked_wizards[0] if linked_wizards else None
        latest_plan = linked_plans[0] if linked_plans else None
        latest_run = None
        if latest_plan is not None:
            plan_runs = [run for run in linked_runs if run.marketing_plan_id == latest_plan.id]
            latest_run = plan_runs[0] if plan_runs else None
        latest_asset = linked_assets[0] if linked_assets else None
        latest_brief = None
        if latest_asset is not None:
            asset_briefs = [brief for brief in linked_briefs if brief.content_asset_id == latest_asset.id]
            latest_brief = asset_briefs[0] if asset_briefs else None
        latest_package = None
        if latest_asset is not None:
            asset_packages = [
                package for package in linked_packages if package.content_asset_id == latest_asset.id
            ]
            latest_package = asset_packages[0] if asset_packages else None
        latest_job = None
        if latest_package is not None:
            package_jobs = [
                job for job in linked_jobs if job.publication_package_id == latest_package.id
            ]
            latest_job = package_jobs[0] if package_jobs else None

        return CampaignArtifacts(
            campaign=campaign,
            wizards=linked_wizards,
            latest_wizard=latest_wizard,
            plans=linked_plans,
            latest_plan=latest_plan,
            runs=linked_runs,
            latest_run=latest_run,
            outputs=linked_outputs,
            content_outputs=content_outputs,
            assets=linked_assets,
            latest_asset=latest_asset,
            briefs=linked_briefs,
            latest_brief=latest_brief,
            media_assets=linked_media,
            packages=linked_packages,
            latest_package=latest_package,
            jobs=linked_jobs,
            latest_job=latest_job,
            skill_runs=skill_runs,
            metrics=metrics,
        )

    @staticmethod
    def _resource_ids(artifacts: CampaignArtifacts) -> CampaignResourceIds:
        content_output = artifacts.content_outputs[0] if artifacts.content_outputs else None
        media_asset = artifacts.media_assets[0] if artifacts.media_assets else None
        return CampaignResourceIds(
            wizard_run_id=artifacts.latest_wizard.id if artifacts.latest_wizard else None,
            marketing_plan_id=artifacts.latest_plan.id if artifacts.latest_plan else None,
            execution_run_id=artifacts.latest_run.id if artifacts.latest_run else None,
            copywriter_output_id=content_output.id if content_output else None,
            content_asset_id=artifacts.latest_asset.id if artifacts.latest_asset else None,
            media_brief_id=artifacts.latest_brief.id if artifacts.latest_brief else None,
            media_asset_id=media_asset.id if media_asset else None,
            publication_package_id=artifacts.latest_package.id if artifacts.latest_package else None,
            publication_package_job_id=artifacts.latest_job.id if artifacts.latest_job else None,
        )

    @staticmethod
    def _extract_error_code(error_field: object | None) -> str | None:
        if not isinstance(error_field, dict):
            return None
        code = error_field.get("error_code")
        if isinstance(code, str) and code.strip():
            return sanitize_text(code).strip()[:64]
        return None

    def _recovery_hint(
        self,
        artifacts: CampaignArtifacts,
    ) -> CampaignFailureRecoveryHint | None:
        wizard = artifacts.latest_wizard
        if wizard is not None and wizard.status == ScenarioWizardRunStatus.FAILED:
            return CampaignFailureRecoveryHint(
                failed_object_type="scenario_wizard_run",
                failed_object_id=wizard.id,
                error_code="wizard_run_failed",
                suggested_recovery=(
                    "Review the wizard failure reason, fix the underlying resource, "
                    "then start a new wizard run from the campaign."
                ),
            )

        run = artifacts.latest_run
        if run is not None and run.status == MarketingPlanExecutionStatus.FAILED:
            return CampaignFailureRecoveryHint(
                failed_object_type="marketing_plan_execution_run",
                failed_object_id=run.id,
                error_code="execution_run_failed",
                suggested_recovery=(
                    "Open the execution run, re-run failed specialists manually, "
                    "or create a new execution run from the approved plan."
                ),
            )

        job = artifacts.latest_job
        if job is not None and job.status == PublicationPackageJobStatus.FAILED:
            error_code = self._extract_error_code(getattr(job, "error", None)) or "publication_job_failed"
            return CampaignFailureRecoveryHint(
                failed_object_type="publication_package_job",
                failed_object_id=job.id,
                error_code=error_code,
                suggested_recovery=(
                    "Check channel configuration and approval gates, then create "
                    "a new dry-run job — control center does not auto-retry."
                ),
            )

        return None

    def _build_timeline(self, artifacts: CampaignArtifacts) -> list[CampaignTimelineEvent]:
        events: list[CampaignTimelineEvent] = []

        for wizard in artifacts.wizards:
            completed_steps = list((wizard.step_results or {}).get("steps_completed") or [])
            for step in completed_steps:
                if step not in SCENARIO_WIZARD_STEPS:
                    continue
                events.append(
                    CampaignTimelineEvent(
                        event_type=CampaignTimelineEventType.WIZARD_STEP,
                        label=step.replace("_", " "),
                        status="completed",
                        resource_id=wizard.id,
                        occurred_at=wizard.updated_at or wizard.created_at,
                        safe_summary=f"Wizard step {step}",
                    ),
                )
            if wizard.status not in _TERMINAL_WIZARD:
                events.append(
                    CampaignTimelineEvent(
                        event_type=CampaignTimelineEventType.WIZARD_STEP,
                        label=wizard.current_step.replace("_", " "),
                        status=wizard.status.value,
                        resource_id=wizard.id,
                        occurred_at=wizard.updated_at or wizard.created_at,
                        safe_summary="Current wizard step",
                    ),
                )

        for plan in artifacts.plans:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.PLAN,
                    label="Marketing plan",
                    status=plan.status.value,
                    resource_id=plan.id,
                    occurred_at=plan.created_at,
                    safe_summary=(plan.title[:120] if plan.title else None),
                ),
            )

        for run in artifacts.runs:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.EXECUTION_RUN,
                    label="Execution run",
                    status=run.status.value,
                    resource_id=run.id,
                    occurred_at=run.created_at,
                    safe_summary=f"Plan version {run.marketing_plan_version_number}",
                ),
            )

        for output in artifacts.outputs:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.SPECIALIST_OUTPUT,
                    label=output.specialist.value,
                    status=output.status.value,
                    resource_id=output.id,
                    occurred_at=output.created_at,
                    safe_summary=(output.title[:120] if output.title else None),
                ),
            )

        for asset in artifacts.assets:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.CONTENT_ASSET,
                    label="Content asset",
                    status=asset.status.value,
                    resource_id=asset.id,
                    occurred_at=asset.created_at,
                    safe_summary=(asset.title[:120] if asset.title else None),
                ),
            )

        for brief in artifacts.briefs:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.MEDIA_BRIEF,
                    label="Media brief",
                    status=brief.status.value,
                    resource_id=brief.id,
                    occurred_at=brief.created_at,
                    safe_summary=(brief.title[:120] if getattr(brief, "title", None) else None),
                ),
            )

        for package in artifacts.packages:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.PUBLICATION_PACKAGE,
                    label="Publication package",
                    status=package.status.value,
                    resource_id=package.id,
                    occurred_at=package.created_at,
                    safe_summary=package.channel.value if package.channel else None,
                ),
            )

        for job in artifacts.jobs:
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.PUBLICATION_JOB,
                    label="Publication job",
                    status=job.status.value,
                    resource_id=job.id,
                    occurred_at=job.created_at,
                    safe_summary=job.schedule_status.value if job.schedule_status else None,
                ),
            )

        for skill_run in artifacts.skill_runs:
            if skill_run.status != MarketingSkillRunStatus.SUCCEEDED:
                continue
            events.append(
                CampaignTimelineEvent(
                    event_type=CampaignTimelineEventType.SKILL_RUN,
                    label=skill_run.skill_type.value.replace("_", " "),
                    status=skill_run.status.value,
                    resource_id=skill_run.id,
                    occurred_at=skill_run.finished_at or skill_run.created_at,
                    safe_summary=f"Skill run {skill_run.skill_type.value}",
                ),
            )

        events.sort(key=lambda item: item.occurred_at)
        return events

    @staticmethod
    def _progress_percent(artifacts: CampaignArtifacts) -> int:
        wizard = artifacts.latest_wizard
        if wizard is not None:
            completed = len((wizard.step_results or {}).get("steps_completed") or [])
            if wizard.status == ScenarioWizardRunStatus.SUCCEEDED:
                return 100
            return min(99, int(completed / _WIZARD_STEP_COUNT * 100))

        milestones = 0
        if artifacts.latest_plan is not None:
            milestones += 1
        if artifacts.latest_plan and artifacts.latest_plan.status == MarketingPlanStatus.APPROVED:
            milestones += 1
        if artifacts.latest_run is not None:
            milestones += 1
        if artifacts.latest_run and artifacts.latest_run.status == MarketingPlanExecutionStatus.SUCCEEDED:
            milestones += 1
        if artifacts.latest_asset is not None:
            milestones += 1
        if artifacts.latest_asset and artifacts.latest_asset.status == ContentAssetStatus.APPROVED:
            milestones += 1
        if artifacts.latest_brief is not None:
            milestones += 1
        if artifacts.latest_package is not None:
            milestones += 1
        if artifacts.latest_job is not None:
            milestones += 1
        return min(100, int(milestones / 9 * 100))

    def _safe_warnings(self, artifacts: CampaignArtifacts) -> list[str]:
        warnings: list[str] = []
        campaign = artifacts.campaign
        if not campaign.scenario_id:
            warnings.append("Attach a marketing scenario before starting the wizard.")
        if campaign.status == CampaignStatus.PAUSED:
            warnings.append("Campaign is paused — resume when ready to continue manual steps.")
        if campaign.status == CampaignStatus.ARCHIVED:
            warnings.append("Archived campaigns are read-only.")
        if not artifacts.plans and campaign.scenario_id:
            warnings.append("No marketing plan linked yet — start the scenario wizard.")
        if artifacts.latest_asset and artifacts.latest_asset.status == ContentAssetStatus.DRAFT:
            warnings.append("Content asset is still draft — submit for review before approval.")
        if artifacts.latest_package and artifacts.latest_package.status != PublicationPackageStatus.APPROVED:
            warnings.append("Publication package must be approved before scheduling.")
        return warnings

    @staticmethod
    def _tool_suggestions(campaign: CampaignTable) -> list:
        metadata = campaign.campaign_metadata or {}
        raw_intent = metadata.get("source_business_intent")
        if not isinstance(raw_intent, dict) or not raw_intent.get("goal"):
            return []
        intent = BusinessIntent(
            goal=str(raw_intent.get("goal") or "promo"),
            industry=raw_intent.get("industry"),
            business_type=raw_intent.get("business_type"),
            campaign_type=raw_intent.get("campaign_type"),
            confidence=float(raw_intent.get("confidence") or 0.0),
            recommended_scenario=raw_intent.get("recommended_scenario"),
        )
        return build_tool_suggestions(intent)

    async def _load_brief_for_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign: CampaignTable,
    ) -> CampaignBriefFields | None:
        metadata = campaign.campaign_metadata or {}
        brief_id_raw = metadata.get("source_campaign_brief_id")
        if not brief_id_raw:
            return None
        from app.services.campaign_brief_service import CampaignBriefService

        brief_row = await CampaignBriefService(self._session).get_by_id(
            owner_id,
            project_id,
            UUID(str(brief_id_raw)),
        )
        if brief_row is None:
            return None
        return CampaignBriefFields(
            business_name=brief_row.business_name,
            industry=brief_row.industry,
            offer=brief_row.offer,
            target_audience=brief_row.target_audience,
            geography=brief_row.geography,
            channels=list(brief_row.channels or []),
            budget_range=brief_row.budget_range,
            deadline=brief_row.deadline,
            constraints=brief_row.constraints,
            success_metric=brief_row.success_metric,
            goal=brief_row.goal,
        )

    async def _skill_suggestions(
        self,
        artifacts: CampaignArtifacts,
        next_action: CampaignNextAction,
        health_status: CampaignHealthStatus,
    ) -> list[CampaignSkillSuggestion]:
        campaign = artifacts.campaign
        metadata = campaign.campaign_metadata or {}
        raw_intent = metadata.get("source_business_intent")
        if not isinstance(raw_intent, dict) or not raw_intent.get("goal"):
            return []
        intent = BusinessIntent(
            goal=str(raw_intent.get("goal") or "promo"),
            industry=raw_intent.get("industry"),
            business_type=raw_intent.get("business_type"),
            campaign_type=raw_intent.get("campaign_type"),
            confidence=float(raw_intent.get("confidence") or 0.0),
            recommended_scenario=raw_intent.get("recommended_scenario"),
        )
        brief = await self._load_brief_for_campaign(
            campaign.owner_id,
            campaign.project_id,
            campaign,
        )
        completed = {
            run.skill_type
            for run in artifacts.skill_runs
            if run.status == MarketingSkillRunStatus.SUCCEEDED
        }
        return build_campaign_skill_suggestions(
            CampaignSkillSuggestionInput(
                intent=intent,
                brief=brief,
                scenario_id=campaign.scenario_id,
                health_status=health_status,
                next_action_type=next_action.action_type,
                skill_context=CampaignSkillContextService.skill_context_from_campaign(campaign),
                completed_skill_types=completed,
                has_plan=artifacts.latest_plan is not None,
                has_content_asset=artifacts.latest_asset is not None,
            ),
        )

    def _resolve_next_action(
        self,
        artifacts: CampaignArtifacts,
        resource_ids: CampaignResourceIds,
    ) -> tuple[CampaignNextAction, CampaignHealthStatus, str | None]:
        campaign = artifacts.campaign
        wizard = artifacts.latest_wizard
        plan = artifacts.latest_plan
        run = artifacts.latest_run
        content_output = artifacts.content_outputs[0] if artifacts.content_outputs else None
        asset = artifacts.latest_asset
        brief = artifacts.latest_brief
        package = artifacts.latest_package
        job = artifacts.latest_job

        recovery = self._recovery_hint(artifacts)
        if recovery is not None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.NONE,
                    label="Resolve failure",
                    safe_description=recovery.suggested_recovery,
                    resource_ids={
                        "failed_object_id": str(recovery.failed_object_id),
                        "failed_object_type": recovery.failed_object_type,
                    },
                ),
                CampaignHealthStatus.FAILED,
                recovery.suggested_recovery,
            )

        if wizard is not None and wizard.status not in _TERMINAL_WIZARD:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.ADVANCE_WIZARD,
                    label="Advance wizard step",
                    safe_description=(
                        f"Run the next wizard step manually: {wizard.current_step.replace('_', ' ')}."
                    ),
                    resource_ids={"wizard_run_id": str(wizard.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if wizard is not None and wizard.status == ScenarioWizardRunStatus.SUCCEEDED:
            if job is not None and job.status in {
                PublicationPackageJobStatus.QUEUED,
                PublicationPackageJobStatus.DRY_RUN_SUCCEEDED,
            }:
                return (
                    CampaignNextAction(
                        action_type=CampaignNextActionType.SCHEDULE_OR_DRY_RUN,
                        label="Dry-run job ready",
                        safe_description=(
                            "Publication package job is queued. Schedule or dispatch dry-run manually."
                        ),
                        resource_ids={"publication_package_job_id": str(job.id)},
                    ),
                    CampaignHealthStatus.COMPLETED,
                    None,
                )

        if not campaign.scenario_id:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.ATTACH_SCENARIO,
                    label="Attach scenario",
                    safe_description="Set scenario_id on the campaign to pick a business template.",
                    resource_ids={"campaign_id": str(campaign.id)},
                ),
                CampaignHealthStatus.BLOCKED,
                "Campaign has no scenario_id.",
            )

        if plan is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.START_WIZARD,
                    label="Start scenario wizard",
                    safe_description="Create a wizard run from the campaign to build plan and artifacts.",
                    resource_ids={"campaign_id": str(campaign.id)},
                ),
                CampaignHealthStatus.HEALTHY,
                None,
            )

        if plan.status == MarketingPlanStatus.DRAFT:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.APPROVE_PLAN,
                    label="Approve marketing plan",
                    safe_description="Approve the draft plan before starting execution.",
                    resource_ids={"marketing_plan_id": str(plan.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Marketing plan must be approved.",
            )

        if run is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.START_EXECUTION,
                    label="Start execution run",
                    safe_description="Create and start a marketing plan execution run.",
                    resource_ids={"marketing_plan_id": str(plan.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "No execution run linked to the approved plan.",
            )

        if run.status == MarketingPlanExecutionStatus.RUNNING:
            snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
            pending = [
                snapshot.specialist
                for snapshot in snapshots
                if snapshot.status != MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED
                and snapshot.specialist in _PIPELINE
            ]
            if pending:
                specialist = pending[0]
                return (
                    CampaignNextAction(
                        action_type=CampaignNextActionType.EXECUTE_NEXT_SPECIALIST,
                        label=f"Execute {specialist.value}",
                        safe_description="Run the next specialist task on the execution run.",
                        resource_ids={
                            "execution_run_id": str(run.id),
                            "specialist": specialist.value,
                        },
                    ),
                    CampaignHealthStatus.WAITING_FOR_USER,
                    None,
                )

        if run.status != MarketingPlanExecutionStatus.SUCCEEDED:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.EXECUTE_NEXT_SPECIALIST,
                    label="Complete execution run",
                    safe_description="Finish remaining specialist tasks on the execution run.",
                    resource_ids={"execution_run_id": str(run.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Execution run has not completed successfully.",
            )

        if content_output is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.EXECUTE_NEXT_SPECIALIST,
                    label="Run copywriter specialist",
                    safe_description="Execute copywriter or sales copywriter on the execution run.",
                    resource_ids={"execution_run_id": str(run.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if content_output.status != MarketingSpecialistOutputStatus.APPROVED:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.APPROVE_COPYWRITER_OUTPUT,
                    label="Approve copywriter output",
                    safe_description="Approve specialist output before creating a content asset.",
                    resource_ids={"copywriter_output_id": str(content_output.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Copywriter output must be approved.",
            )

        if asset is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.CREATE_CONTENT_ASSET,
                    label="Create content asset",
                    safe_description="Convert approved copywriter output into a content asset.",
                    resource_ids={
                        "copywriter_output_id": str(content_output.id),
                        "marketing_plan_id": str(plan.id),
                    },
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if asset.status == ContentAssetStatus.DRAFT:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.APPROVE_ASSET,
                    label="Submit and approve content asset",
                    safe_description="Submit the draft asset for review, then approve it.",
                    resource_ids={"content_asset_id": str(asset.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Content asset is still draft.",
            )

        if asset.status == ContentAssetStatus.REVIEW:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.APPROVE_ASSET,
                    label="Approve content asset",
                    safe_description="Approve the content asset for media and publishing steps.",
                    resource_ids={"content_asset_id": str(asset.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Content asset awaiting approval.",
            )

        if brief is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.CREATE_MEDIA_BRIEF,
                    label="Create media brief",
                    safe_description="Create a media brief from the approved content asset.",
                    resource_ids={"content_asset_id": str(asset.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if brief.status != MediaBriefStatus.APPROVED:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.APPROVE_MEDIA_BRIEF,
                    label="Approve media brief",
                    safe_description="Submit and approve the media brief before publication packaging.",
                    resource_ids={"media_brief_id": str(brief.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Media brief must be approved.",
            )

        if package is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.CREATE_PUBLICATION_PACKAGE,
                    label="Create publication package",
                    safe_description="Create a publication package from the approved content asset.",
                    resource_ids={"content_asset_id": str(asset.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if package.status != PublicationPackageStatus.APPROVED:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.CREATE_PUBLICATION_PACKAGE,
                    label="Approve publication package",
                    safe_description="Submit and approve the publication package before creating a job.",
                    resource_ids={"publication_package_id": str(package.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                "Publication package must be approved.",
            )

        if job is None:
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.SCHEDULE_OR_DRY_RUN,
                    label="Create dry-run publication job",
                    safe_description="Create a queued publication package job (dry-run only).",
                    resource_ids={"publication_package_id": str(package.id)},
                ),
                CampaignHealthStatus.WAITING_FOR_USER,
                None,
            )

        if job is not None and (
            job.status
            in {
                PublicationPackageJobStatus.QUEUED,
                PublicationPackageJobStatus.DRY_RUN_SUCCEEDED,
            }
            or getattr(job, "schedule_status", None) == PublicationPackageJobScheduleStatus.SCHEDULED
        ):
            return (
                CampaignNextAction(
                    action_type=CampaignNextActionType.SCHEDULE_OR_DRY_RUN,
                    label="Schedule or dispatch dry-run",
                    safe_description="Job is queued — schedule or dispatch dry-run manually when ready.",
                    resource_ids={"publication_package_job_id": str(job.id)},
                ),
                CampaignHealthStatus.COMPLETED,
                None,
            )

        _ = resource_ids
        return (
            CampaignNextAction(
                action_type=CampaignNextActionType.NONE,
                label="No action",
                safe_description="Campaign pipeline has no pending recommendation.",
                resource_ids={},
            ),
            CampaignHealthStatus.HEALTHY,
            None,
        )

    async def get_control_center(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignControlCenter | None:
        artifacts = await self._load_artifacts(owner_id, project_id, campaign_id)
        if artifacts is None or artifacts.metrics is None:
            return None

        resource_ids = self._resource_ids(artifacts)
        next_action, health_status, blocking_reason = self._resolve_next_action(
            artifacts,
            resource_ids,
        )
        recovery = self._recovery_hint(artifacts)
        timeline = self._build_timeline(artifacts)
        warnings = self._safe_warnings(artifacts)
        health = CampaignHealth(
            status=health_status,
            blocking_reason=blocking_reason,
            progress_percent=self._progress_percent(artifacts),
        )

        from app.services.campaign_action_builder import build_campaign_actions

        skill_suggestions = await self._skill_suggestions(
            artifacts,
            next_action,
            health_status,
        )
        skill_context = CampaignSkillContextService.skill_context_from_campaign(artifacts.campaign)
        latest_skill_runs = [
            marketing_skill_run_to_contract(row) for row in artifacts.skill_runs[:10]
        ]

        primary_action, available_actions = build_campaign_actions(
            artifacts,
            next_action,
            resource_ids,
            health_status=health_status,
            skill_suggestions=skill_suggestions,
        )

        from app.services.campaign_supervisor_service import CampaignSupervisorService
        from app.services.campaign_workflow_service import CampaignWorkflowService

        supervisor_report = await CampaignSupervisorService(self._session).get_report(
            owner_id,
            project_id,
            campaign_id,
            audit=False,
        )
        supervisor_summary = (
            CampaignSupervisorService.summarize_for_control_center(supervisor_report)
            if supervisor_report is not None
            else {
                "supervisor_health_score": 100,
                "supervisor_findings_count": 0,
                "critical_findings_count": 0,
                "top_findings": [],
            }
        )

        workflow_service = CampaignWorkflowService(self._session)
        workflow_suggestions = await workflow_service.recommend(
            owner_id,
            project_id,
            campaign_id,
        )
        active_workflow = await workflow_service.get_active_run_summary(
            owner_id,
            project_id,
            campaign_id,
        )

        return CampaignControlCenter(
            campaign=campaign_to_contract(artifacts.campaign),
            health=health,
            next_action=next_action,
            timeline=timeline,
            metrics=artifacts.metrics,
            resource_ids=resource_ids,
            safe_warnings=warnings,
            recovery_hint=recovery,
            primary_action=primary_action,
            available_actions=available_actions,
            tool_suggestions=self._tool_suggestions(artifacts.campaign),
            skill_suggestions=skill_suggestions,
            latest_skill_runs=latest_skill_runs,
            skill_context=skill_context,
            **supervisor_summary,
            workflow_suggestions=workflow_suggestions,
            active_workflow=active_workflow,
        )

    async def get_summary(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignControlCenterSummary | None:
        center = await self.get_control_center(owner_id, project_id, campaign_id)
        if center is None:
            return None
        return CampaignControlCenterSummary(
            campaign=center.campaign,
            health=center.health,
            next_action_type=center.next_action.action_type,
        )

    async def list_summaries(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        health: CampaignHealthStatus | None = None,
        next_action_type: CampaignNextActionType | None = None,
        failed_only: bool = False,
        completed_only: bool = False,
        query: str | None = None,
        scenario_id: str | None = None,
        status: CampaignStatus | None = None,
        limit: int = 50,
    ) -> list[CampaignControlCenterSummary] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        if query or scenario_id or status is not None:
            rows = await self._layer.search(
                owner_id,
                project_id,
                query=query,
                scenario_id=scenario_id,
                status=status,
                limit=limit,
            )
        else:
            rows = await self._layer.list_by_project(owner_id, project_id, limit=limit)

        if rows is None:
            return None

        summaries: list[CampaignControlCenterSummary] = []
        for row in rows:
            summary = await self.get_summary(owner_id, project_id, row.id)
            if summary is None:
                continue
            if health is not None and summary.health.status != health:
                continue
            if next_action_type is not None and summary.next_action_type != next_action_type:
                continue
            if failed_only and summary.health.status != CampaignHealthStatus.FAILED:
                continue
            if completed_only and summary.health.status != CampaignHealthStatus.COMPLETED:
                continue
            summaries.append(summary)
        return summaries

"""E2E demo flow status — read-only aggregate (Phase AI.81)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.media_generation.contracts import MediaGenerationJobStatus
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.schemas.contracts import (
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.schemas.demo_flow import DemoFlowStatusResponse
from app.services.e2e_demo_seed_service import E2E_DEMO_MARKER, E2E_DEMO_PLAN_TITLE
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService
from app.services.projects_service import ProjectService

_PIPELINE = MarketingPipelineExecutionService.pipeline_order()


class DemoFlowStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)

    async def get_status(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> DemoFlowStatusResponse | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None

        plans = await MarketingPlanRepository(self._session).list_by_project(
            owner_id,
            project_id,
            limit=20,
        )
        plan = next(
            (
                p
                for p in plans
                if p.title == E2E_DEMO_PLAN_TITLE
                or (isinstance(p.project_context, dict) and p.project_context.get("demo_seed") == E2E_DEMO_MARKER)
            ),
            plans[0] if plans else None,
        )

        links: dict[str, str] = {}
        completed_specialists: list[str] = []
        marketing_plan_status: str | None = None
        execution_run_status: str | None = None
        content_asset_status: str | None = None
        media_brief_status: str | None = None
        media_asset_status: str | None = None
        publication_package_status: str | None = None
        publication_job_status: str | None = None
        publication_schedule_status: str | None = None
        next_action: str | None = None
        run = None
        copywriter_outputs: list = []
        asset = None
        briefs: list = []
        packages: list = []
        jobs: list = []

        if plan is not None:
            marketing_plan_status = plan.status.value
            links["marketing_plan_id"] = str(plan.id)

            runs = await MarketingPlanExecutionRunRepository(self._session).list_by_project(
                owner_id,
                project_id,
                marketing_plan_id=plan.id,
                limit=1,
            )
            run = runs[0] if runs else None
            if run is not None:
                execution_run_status = run.status.value
                links["execution_run_id"] = str(run.id)
                snapshots = MarketingPlanExecutionService.task_snapshots_for_row(run)
                for snapshot in snapshots:
                    if snapshot.status == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED:
                        completed_specialists.append(snapshot.specialist.value)

                copywriter_outputs = await MarketingSpecialistOutputRepository(
                    self._session,
                ).list_by_project(
                    owner_id,
                    project_id,
                    execution_run_id=run.id,
                    specialist=MarketingSpecialistType.COPYWRITER,
                    limit=1,
                )
                if copywriter_outputs:
                    links["copywriter_output_id"] = str(copywriter_outputs[0].id)
                    if copywriter_outputs[0].status != MarketingSpecialistOutputStatus.APPROVED:
                        next_action = next_action or "approve_copywriter_output"

                assets = await ContentAssetRepository(self._session).list_by_project(
                    owner_id,
                    project_id,
                    limit=20,
                )
                asset = next(
                    (
                        a
                        for a in assets
                        if a.source_marketing_plan_id == plan.id
                        or a.source_execution_run_id == run.id
                    ),
                    assets[0] if assets else None,
                )
                if asset is not None:
                    content_asset_status = asset.status.value
                    links["content_asset_id"] = str(asset.id)
                    if asset.status != ContentAssetStatus.APPROVED:
                        next_action = next_action or "approve_content_asset"

                    briefs = await MediaBriefRepository(self._session).list_by_project(
                        owner_id,
                        project_id,
                        content_asset_id=asset.id,
                        limit=1,
                    )
                    if briefs:
                        media_brief_status = briefs[0].status.value
                        links["media_brief_id"] = str(briefs[0].id)
                        if briefs[0].status != MediaBriefStatus.APPROVED:
                            next_action = next_action or "approve_media_brief"

                        media_assets = await MediaAssetRepository(self._session).list_by_project(
                            owner_id,
                            project_id,
                            media_brief_id=briefs[0].id,
                            limit=1,
                        )
                        if media_assets:
                            media_asset_status = media_assets[0].status.value
                            links["media_asset_id"] = str(media_assets[0].id)
                        else:
                            next_action = next_action or "create_media_asset"

                    packages = await PublicationPackageRepository(self._session).list_by_project(
                        owner_id,
                        project_id,
                        content_asset_id=asset.id,
                        limit=1,
                    )
                    if packages:
                        publication_package_status = packages[0].status.value
                        links["publication_package_id"] = str(packages[0].id)
                        if packages[0].status != PublicationPackageStatus.APPROVED:
                            next_action = next_action or "approve_publication_package"

                        jobs = await PublicationPackageJobRepository(self._session).list_by_project(
                            owner_id,
                            project_id,
                            publication_package_id=packages[0].id,
                            limit=1,
                        )
                        if jobs:
                            publication_job_status = jobs[0].status.value
                            publication_schedule_status = jobs[0].schedule_status.value
                            links["publication_package_job_id"] = str(jobs[0].id)
                        else:
                            next_action = next_action or "create_publication_package_job"
                    else:
                        next_action = next_action or "create_publication_package"
                elif copywriter_outputs and copywriter_outputs[0].status == MarketingSpecialistOutputStatus.APPROVED:
                    next_action = next_action or "create_content_asset"
                elif plan.status == MarketingPlanStatus.APPROVED:
                    pending = [
                        s.specialist.value
                        for s in snapshots
                        if s.status != MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED
                        and s.specialist in _PIPELINE
                    ]
                    if pending:
                        next_action = next_action or f"execute_specialist:{pending[0]}"
                    elif execution_run_status != "succeeded":
                        next_action = next_action or "complete_execution_run"
            elif plan.status == MarketingPlanStatus.APPROVED:
                next_action = next_action or "start_execution_run"
        else:
            next_action = "create_marketing_plan"

        if plan is not None and plan.status == MarketingPlanStatus.DRAFT:
            next_action = "approve_marketing_plan"

        if next_action is None:
            next_action = "dispatch_dry_run_or_schedule"

        failed_step, blocking_reason, last_error_code = self._failure_markers(
            plan=plan,
            run=run if plan is not None else None,
            copywriter_outputs=copywriter_outputs if plan is not None and run is not None else [],
            asset=asset if plan is not None and run is not None else None,
            briefs=briefs if plan is not None and run is not None and asset is not None else [],
            packages=packages if plan is not None and run is not None and asset is not None else [],
            jobs=jobs if plan is not None and run is not None and asset is not None and packages else [],
            marketing_plan_status=marketing_plan_status,
            execution_run_status=execution_run_status,
            content_asset_status=content_asset_status,
            media_brief_status=media_brief_status,
            media_asset_status=media_asset_status,
            publication_package_status=publication_package_status,
            publication_job_status=publication_job_status,
            next_action=next_action,
        )

        return DemoFlowStatusResponse(
            marketing_plan_status=marketing_plan_status,
            execution_run_status=execution_run_status,
            completed_specialists=completed_specialists,
            content_asset_status=content_asset_status,
            media_brief_status=media_brief_status,
            media_asset_status=media_asset_status,
            publication_package_status=publication_package_status,
            publication_job_status=publication_job_status,
            publication_schedule_status=publication_schedule_status,
            next_available_action=next_action,
            resource_links=links,
            failed_step=failed_step,
            blocking_reason=blocking_reason,
            last_error_code=last_error_code,
            suggested_next_action=next_action,
        )

    @staticmethod
    def _extract_error_code(error_field: object | None) -> str | None:
        if not isinstance(error_field, dict):
            return None
        code = error_field.get("error_code")
        if isinstance(code, str) and code.strip():
            return code.strip()[:64]
        return None

    def _failure_markers(
        self,
        *,
        plan: object | None,
        run: object | None,
        copywriter_outputs: list,
        asset: object | None,
        briefs: list,
        packages: list,
        jobs: list,
        marketing_plan_status: str | None,
        execution_run_status: str | None,
        content_asset_status: str | None,
        media_brief_status: str | None,
        media_asset_status: str | None,
        publication_package_status: str | None,
        publication_job_status: str | None,
        next_action: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        last_error_code: str | None = None

        if jobs:
            job = jobs[0]
            if getattr(job, "status", None) == PublicationPackageJobStatus.FAILED:
                last_error_code = self._extract_error_code(getattr(job, "error", None)) or (
                    self._extract_error_code(getattr(job, "last_dispatch_error", None))
                )
                return (
                    "publishing",
                    "Publication job failed; check channel config and approval gates.",
                    last_error_code or "publication_job_failed",
                )
            dispatch_error = getattr(job, "last_dispatch_error", None)
            if dispatch_error:
                last_error_code = self._extract_error_code(dispatch_error)
                return (
                    "publishing",
                    "Scheduled dispatch encountered an error.",
                    last_error_code or "dispatch_failed",
                )

        if run is not None and getattr(run, "status", None) == MarketingPlanExecutionStatus.FAILED:
            return (
                "marketing_pipeline",
                "Marketing execution run failed before content production.",
                "execution_run_failed",
            )

        if plan is None:
            return (
                "marketing_pipeline",
                "No marketing plan found for this project.",
                None,
            )

        if marketing_plan_status == MarketingPlanStatus.DRAFT.value:
            return (
                "marketing_pipeline",
                "Marketing plan must be approved before running specialists.",
                None,
            )

        if run is None and marketing_plan_status == MarketingPlanStatus.APPROVED.value:
            return (
                "marketing_pipeline",
                "Start a marketing execution run from the approved plan.",
                None,
            )

        if execution_run_status not in (None, MarketingPlanExecutionStatus.SUCCEEDED.value):
            if execution_run_status == MarketingPlanExecutionStatus.RUNNING.value:
                return (
                    "marketing_pipeline",
                    "Execution run is still in progress.",
                    None,
                )
            return (
                "marketing_pipeline",
                "Execution run has not completed successfully.",
                last_error_code,
            )

        if copywriter_outputs and copywriter_outputs[0].status != MarketingSpecialistOutputStatus.APPROVED:
            return (
                "content",
                "Copywriter output must be approved before creating a content asset.",
                None,
            )

        if asset is None and copywriter_outputs:
            return (
                "content",
                "Create a content asset from the approved copywriter output.",
                None,
            )

        if content_asset_status and content_asset_status != ContentAssetStatus.APPROVED.value:
            return (
                "content",
                "Content asset must be approved before media and publishing steps.",
                None,
            )

        if briefs and briefs[0].status != MediaBriefStatus.APPROVED.value:
            return (
                "media",
                "Media brief must be approved before placeholder media asset creation.",
                None,
            )

        if asset is not None and not media_asset_status and briefs:
            return (
                "media",
                "Create a placeholder media asset from the approved brief.",
                None,
            )

        if packages and packages[0].status != PublicationPackageStatus.APPROVED.value:
            return (
                "publishing",
                "Publication package must be approved before creating a publish job.",
                None,
            )

        if asset is not None and not packages:
            return (
                "publishing",
                "Create and approve a publication package for the content asset.",
                None,
            )

        if packages and not jobs:
            return (
                "publishing",
                "Create a publication package job on an active channel.",
                None,
            )

        if next_action and next_action != "dispatch_dry_run_or_schedule":
            return (
                next_action.split(":")[0] if ":" in next_action else "onboarding",
                "Complete the next recommended action in the demo checklist.",
                last_error_code,
            )

        return None, None, last_error_code

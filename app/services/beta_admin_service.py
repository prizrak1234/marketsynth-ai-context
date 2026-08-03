"""Beta admin dashboard aggregates (Phase AI.89)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.beta_feedback_reports import BetaFeedbackReportRepository
from app.db.models.project import ProjectTable
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublicationJobTable
from app.db.models.user import UserTable
from app.db.models.media import MediaGenerationJobTable
from app.db.repositories.operational_metrics import metrics_window_start
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.media_generation.contracts import MediaGenerationJobStatus
from app.publishing.contracts import PublicationJobStatus
from app.schemas.beta_admin import (
    BetaAdminDashboardResponse,
    BetaQaDemoCompletionSummary,
    BetaQaExportResponse,
    BetaQaFailedJobsSummary,
    BetaQaFeedbackCounts,
    BetaQaProjectSnapshot,
)
from app.schemas.contracts import BetaFeedbackSeverity, BetaFeedbackStatus
from app.services.e2e_demo_seed_service import E2E_DEMO_PROJECT_NAME
from app.services.demo_flow_status_service import DemoFlowStatusService


class BetaAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self, *, scoped_owner_id: UUID | None = None) -> BetaAdminDashboardResponse:
        since = metrics_window_start()
        users_total = int(
            (await self._session.execute(select(func.count()).select_from(UserTable))).scalar_one()
            or 0,
        )

        project_stmt = select(func.count()).select_from(ProjectTable)
        if scoped_owner_id is not None:
            project_stmt = project_stmt.where(ProjectTable.owner_id == scoped_owner_id)
        projects_total = int((await self._session.execute(project_stmt)).scalar_one() or 0)

        demo_ready = 0
        project_query = select(ProjectTable)
        if scoped_owner_id is not None:
            project_query = project_query.where(ProjectTable.owner_id == scoped_owner_id)
        projects = list((await self._session.execute(project_query.limit(200))).scalars().all())
        demo_service = DemoFlowStatusService(self._session)
        for project in projects:
            if project.name != E2E_DEMO_PROJECT_NAME:
                continue
            status = await demo_service.get_status(project.owner_id, project_id=project.id)
            if status and status.publication_job_status == "queued":
                demo_ready += 1

        pkg_failed_stmt = select(func.count()).select_from(PublicationPackageJobTable).where(
            PublicationPackageJobTable.status == PublicationPackageJobStatus.FAILED,
            PublicationPackageJobTable.created_at >= since,
        )
        gen_failed_stmt = select(func.count()).select_from(MediaGenerationJobTable).where(
            MediaGenerationJobTable.status == MediaGenerationJobStatus.FAILED,
            MediaGenerationJobTable.created_at >= since,
        )
        legacy_failed_stmt = select(func.count()).select_from(PublicationJobTable).where(
            PublicationJobTable.status == PublicationJobStatus.FAILED,
            PublicationJobTable.created_at >= since,
        )
        if scoped_owner_id is not None:
            pkg_failed_stmt = pkg_failed_stmt.where(
                PublicationPackageJobTable.owner_id == scoped_owner_id,
            )
            gen_failed_stmt = gen_failed_stmt.where(
                MediaGenerationJobTable.owner_id == scoped_owner_id,
            )
            legacy_failed_stmt = legacy_failed_stmt.where(
                PublicationJobTable.owner_id == scoped_owner_id,
            )

        latest_candidates: list[datetime] = []
        for model, owner_col in (
            (PublicationPackageJobTable, PublicationPackageJobTable.owner_id),
            (MediaGenerationJobTable, MediaGenerationJobTable.owner_id),
            (PublicationJobTable, PublicationJobTable.owner_id),
        ):
            stmt = select(func.max(model.created_at))
            if scoped_owner_id is not None:
                stmt = stmt.where(owner_col == scoped_owner_id)
            value = (await self._session.execute(stmt)).scalar_one_or_none()
            if value is not None:
                latest_candidates.append(value)

        latest_activity_at = max(latest_candidates) if latest_candidates else None

        return BetaAdminDashboardResponse(
            users_total=users_total if scoped_owner_id is None else 1,
            projects_total=projects_total,
            demo_flow_ready_projects=demo_ready,
            failed_package_jobs=int((await self._session.execute(pkg_failed_stmt)).scalar_one() or 0),
            failed_generation_jobs=int((await self._session.execute(gen_failed_stmt)).scalar_one() or 0),
            failed_legacy_publication_jobs=int(
                (await self._session.execute(legacy_failed_stmt)).scalar_one() or 0,
            ),
            latest_activity_at=latest_activity_at,
            window_hours=24,
        )

    async def get_qa_export(self, *, scoped_owner_id: UUID | None = None) -> BetaQaExportResponse:
        dashboard = await self.get_dashboard(scoped_owner_id=scoped_owner_id)

        project_query = select(ProjectTable)
        if scoped_owner_id is not None:
            project_query = project_query.where(ProjectTable.owner_id == scoped_owner_id)
        projects = list((await self._session.execute(project_query.limit(200))).scalars().all())

        demo_service = DemoFlowStatusService(self._session)
        snapshots: list[BetaQaProjectSnapshot] = []
        demo_total = 0
        queued_count = 0
        failed_step_count = 0

        for project in projects:
            if project.name != E2E_DEMO_PROJECT_NAME:
                continue
            demo_total += 1
            status = await demo_service.get_status(project.owner_id, project_id=project.id)
            if status is None:
                continue
            if status.publication_job_status == "queued":
                queued_count += 1
            if status.failed_step:
                failed_step_count += 1
            snapshots.append(
                BetaQaProjectSnapshot(
                    project_id=project.id,
                    project_name=project.name,
                    publication_job_status=status.publication_job_status,
                    failed_step=status.failed_step,
                    last_error_code=status.last_error_code,
                ),
            )

        feedback_repo = BetaFeedbackReportRepository(self._session)
        status_counts = await feedback_repo.count_by_status(owner_id=scoped_owner_id)
        severity_counts = await feedback_repo.count_by_severity(
            owner_id=scoped_owner_id,
            severities=(BetaFeedbackSeverity.BLOCKER, BetaFeedbackSeverity.HIGH),
        )

        return BetaQaExportResponse(
            generated_at=datetime.now(UTC),
            projects=snapshots,
            demo_completion=BetaQaDemoCompletionSummary(
                demo_projects_total=demo_total,
                publication_queued_count=queued_count,
                with_failed_step_count=failed_step_count,
            ),
            feedback_counts=BetaQaFeedbackCounts(
                open=status_counts.get(BetaFeedbackStatus.OPEN, 0),
                triaged=status_counts.get(BetaFeedbackStatus.TRIAGED, 0),
                resolved=status_counts.get(BetaFeedbackStatus.RESOLVED, 0),
                archived=status_counts.get(BetaFeedbackStatus.ARCHIVED, 0),
                blocker=severity_counts.get(BetaFeedbackSeverity.BLOCKER, 0),
                high=severity_counts.get(BetaFeedbackSeverity.HIGH, 0),
            ),
            failed_jobs=BetaQaFailedJobsSummary(
                failed_package_jobs=dashboard.failed_package_jobs,
                failed_generation_jobs=dashboard.failed_generation_jobs,
                failed_legacy_publication_jobs=dashboard.failed_legacy_publication_jobs,
                window_hours=dashboard.window_hours,
            ),
        )

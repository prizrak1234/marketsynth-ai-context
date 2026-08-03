"""Reset E2E demo artifacts for a project (Phase AI.98)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plan_versions import MarketingPlanVersionRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_output_versions import (
    MarketingSpecialistOutputVersionRepository,
)
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.schemas.contracts import MarketingSpecialistType
from app.services.e2e_demo_seed_service import E2E_DEMO_CHANNEL_NAME, E2E_DEMO_PLAN_TITLE
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


@dataclass(frozen=True)
class E2eDemoResetResult:
    project_id: UUID
    cleared: bool
    removed_counts: dict[str, int]


class E2eDemoResetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _delete_row(self, row: object) -> None:
        await self._session.delete(row)
        await self._session.flush()

    async def reset_project(self, owner_id: UUID, project_id: UUID) -> E2eDemoResetResult | None:
        project = await ProjectService(self._session).get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None

        plans = await MarketingPlanRepository(self._session).list_by_project(
            owner_id,
            project_id,
            limit=50,
        )
        plan = next((p for p in plans if p.title == E2E_DEMO_PLAN_TITLE), None)
        if plan is None:
            return E2eDemoResetResult(project_id=project_id, cleared=False, removed_counts={})

        run_repo = MarketingPlanExecutionRunRepository(self._session)
        runs = await run_repo.list_by_project(
            owner_id,
            project_id,
            marketing_plan_id=plan.id,
            limit=50,
        )
        run_ids = {run.id for run in runs}

        output_repo = MarketingSpecialistOutputRepository(self._session)
        outputs = await output_repo.list_by_project(owner_id, project_id, limit=200)
        demo_outputs = [o for o in outputs if o.execution_run_id in run_ids]
        copywriter = next(
            (o for o in demo_outputs if o.specialist == MarketingSpecialistType.COPYWRITER),
            None,
        )

        asset_repo = ContentAssetRepository(self._session)
        asset = None
        if copywriter is not None:
            asset = await asset_repo.get_by_source_specialist_output_id(
                owner_id,
                project_id,
                copywriter.id,
            )

        counts: dict[str, int] = {}

        async with transactional(self._session):
            if asset is not None:
                jobs_repo = PublicationPackageJobRepository(self._session)
                packages_repo = PublicationPackageRepository(self._session)
                packages = await packages_repo.list_by_project(
                    owner_id,
                    project_id,
                    content_asset_id=asset.id,
                    limit=50,
                )
                job_count = 0
                for package in packages:
                    jobs = await jobs_repo.list_by_project(
                        owner_id,
                        project_id,
                        publication_package_id=package.id,
                        limit=50,
                    )
                    for job in jobs:
                        await self._delete_row(job)
                        job_count += 1
                    await self._delete_row(package)
                counts["publication_package_jobs"] = job_count
                counts["publication_packages"] = len(packages)

                brief_repo = MediaBriefRepository(self._session)
                briefs = await brief_repo.list_by_project(
                    owner_id,
                    project_id,
                    content_asset_id=asset.id,
                    limit=50,
                )
                media_repo = MediaAssetRepository(self._session)
                media_count = 0
                for brief in briefs:
                    media_rows = await media_repo.list_by_project(
                        owner_id,
                        project_id,
                        media_brief_id=brief.id,
                        limit=50,
                    )
                    for media in media_rows:
                        await self._delete_row(media)
                        media_count += 1
                    await self._delete_row(brief)
                counts["media_assets"] = media_count
                counts["media_briefs"] = len(briefs)

                version_repo = ContentAssetVersionRepository(self._session)
                versions = await version_repo.list_versions(asset.id, owner_id, project_id)
                for version in versions:
                    await self._delete_row(version)
                await self._delete_row(asset)
                counts["content_assets"] = 1

            channels_repo = PublishingChannelRepository(self._session)
            channels = await channels_repo.list_for_project(
                project_id,
                owner_id=owner_id,
                include_archived=True,
                limit=100,
            )
            demo_channels = [c for c in channels if c.name == E2E_DEMO_CHANNEL_NAME]
            for channel in demo_channels:
                await self._delete_row(channel)
            counts["foundation_channels"] = len(demo_channels)

            out_version_repo = MarketingSpecialistOutputVersionRepository(self._session)
            for output in demo_outputs:
                versions = await out_version_repo.list_for_output(output.id, limit=100)
                for version in versions:
                    await self._delete_row(version)
                await self._delete_row(output)
            counts["specialist_outputs"] = len(demo_outputs)

            for run in runs:
                await self._delete_row(run)
            counts["execution_runs"] = len(runs)

            plan_version_repo = MarketingPlanVersionRepository(self._session)
            plan_versions = await plan_version_repo.list_for_plan(plan.id, limit=100)
            for version in plan_versions:
                await self._delete_row(version)
            counts["plan_versions"] = len(plan_versions)

            plan_repo = MarketingPlanRepository(self._session)
            await self._delete_row(plan)
            counts["marketing_plans"] = 1

        return E2eDemoResetResult(project_id=project_id, cleared=True, removed_counts=counts)

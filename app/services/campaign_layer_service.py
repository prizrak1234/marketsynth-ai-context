"""Business campaign layer service (Phase AI.148–AI.153)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.campaign import CampaignTable
from app.db.repositories.campaigns import CampaignRepository
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.marketing_plan_execution_runs import MarketingPlanExecutionRunRepository
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.db.repositories.marketing_specialist_outputs import MarketingSpecialistOutputRepository
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.scenario_wizard_runs import ScenarioWizardRunRepository
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import CampaignDashboard, CampaignMetrics, CampaignStatus
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_NAME_MAX = 256
_GOAL_MAX = 4096
_CAMPAIGN_UPDATE_FIELDS = frozenset({"name", "goal", "scenario_id", "status", "metadata"})


def campaign_id_in_context(context: dict[str, Any] | None, campaign_id: UUID) -> bool:
    if not context:
        return False
    raw = context.get("source_campaign_id")
    return raw is not None and str(raw) == str(campaign_id)


class CampaignLayerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignRepository(session)
        self._projects = ProjectService(session)
        self._plans = MarketingPlanRepository(session)
        self._runs = MarketingPlanExecutionRunRepository(session)
        self._outputs = MarketingSpecialistOutputRepository(session)
        self._assets = ContentAssetRepository(session)
        self._briefs = MediaBriefRepository(session)
        self._media_assets = MediaAssetRepository(session)
        self._packages = PublicationPackageRepository(session)
        self._jobs = PublicationPackageJobRepository(session)
        self._wizards = ScenarioWizardRunRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _assert_not_archived(row: CampaignTable) -> None:
        if row.status == CampaignStatus.ARCHIVED:
            raise InvalidStateError("Archived campaigns cannot be modified")

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        name: str,
        goal: str,
        scenario_id: str | None = None,
        status: CampaignStatus = CampaignStatus.DRAFT,
        metadata: dict[str, Any] | None = None,
    ) -> CampaignTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if scenario_id is not None and get_scenario(scenario_id) is None:
            raise InvalidStateError("Unknown marketing scenario_id")

        row = CampaignTable(
            owner_id=owner_id,
            project_id=project_id,
            name=sanitize_text(name).strip()[:_NAME_MAX],
            goal=sanitize_text(goal).strip()[:_GOAL_MAX],
            scenario_id=scenario_id,
            status=status,
            campaign_metadata=sanitize_payload(metadata or {}) or {},
        )
        async with transactional(self._session):
            return await self._campaigns.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignTable | None:
        return await self._campaigns.get_by_id_for_owner(campaign_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: CampaignStatus | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[CampaignTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._campaigns.list_by_project(
            owner_id,
            project_id,
            status=status,
            include_archived=include_archived,
            limit=limit,
        )

    async def search(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        query: str | None = None,
        scenario_id: str | None = None,
        status: CampaignStatus | None = None,
        limit: int = 50,
    ) -> list[CampaignTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._campaigns.search(
            owner_id,
            project_id,
            query=query,
            scenario_id=scenario_id,
            status=status,
            limit=limit,
        )

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        updates: dict[str, Any],
    ) -> CampaignTable | None:
        row = await self.get(owner_id, project_id, campaign_id)
        if row is None:
            return None
        self._assert_not_archived(row)

        filtered: dict[str, Any] = {}
        for key, value in updates.items():
            if key == "metadata":
                filtered["campaign_metadata"] = sanitize_payload(value or {}) or {}
            elif key in _CAMPAIGN_UPDATE_FIELDS and key != "metadata":
                filtered[key] = value

        if "scenario_id" in filtered and filtered["scenario_id"] is not None:
            if get_scenario(str(filtered["scenario_id"])) is None:
                raise InvalidStateError("Unknown marketing scenario_id")
        if "name" in filtered and isinstance(filtered["name"], str):
            filtered["name"] = sanitize_text(filtered["name"]).strip()[:_NAME_MAX]
        if "goal" in filtered and isinstance(filtered["goal"], str):
            filtered["goal"] = sanitize_text(filtered["goal"]).strip()[:_GOAL_MAX]

        if not filtered:
            return row

        async with transactional(self._session):
            for key, value in filtered.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            return await self._campaigns.update(row)

    async def compute_metrics(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignMetrics | None:
        campaign = await self.get(owner_id, project_id, campaign_id)
        if campaign is None:
            return None

        plans = await self._plans.list_by_project(owner_id, project_id, limit=200)
        linked_plan_ids = [
            plan.id for plan in plans if campaign_id_in_context(plan.project_context, campaign_id)
        ]

        runs = await self._runs.list_by_project(owner_id, project_id, limit=200)
        linked_run_ids = {run.id for run in runs if run.marketing_plan_id in linked_plan_ids}

        outputs = await self._outputs.list_by_project(owner_id, project_id, limit=500)
        linked_outputs = [output for output in outputs if output.execution_run_id in linked_run_ids]

        assets = await self._assets.list_by_project(owner_id, project_id, limit=500)
        linked_assets = [
            asset
            for asset in assets
            if campaign_id_in_context(asset.asset_metadata, campaign_id)
            or asset.source_marketing_plan_id in linked_plan_ids
        ]
        linked_asset_ids = {asset.id for asset in linked_assets}

        media_rows = await self._media_assets.list_by_project(owner_id, project_id, limit=500)
        briefs = await self._briefs.list_by_project(owner_id, project_id, limit=500)
        linked_brief_ids = {
            brief.id for brief in briefs if brief.content_asset_id in linked_asset_ids
        }
        linked_media = [media for media in media_rows if media.media_brief_id in linked_brief_ids]

        packages = await self._packages.list_by_project(owner_id, project_id, limit=500)
        linked_packages = [
            package for package in packages if package.content_asset_id in linked_asset_ids
        ]
        linked_package_ids = {package.id for package in linked_packages}

        jobs = await self._jobs.list_by_project(owner_id, project_id, limit=500)
        linked_jobs = [job for job in jobs if job.publication_package_id in linked_package_ids]

        wizards = await self._wizards.list_by_project(owner_id, project_id, limit=100)
        linked_wizards = [wizard for wizard in wizards if wizard.source_campaign_id == campaign_id]

        return CampaignMetrics(
            plans_total=len(linked_plan_ids),
            outputs_total=len(linked_outputs),
            assets_total=len(linked_assets),
            media_total=len(linked_media),
            packages_total=len(linked_packages),
            jobs_total=len(linked_jobs),
            wizard_runs_total=len(linked_wizards),
        )

    async def get_dashboard(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignDashboard | None:
        from app.api.mappers import campaign_to_contract

        campaign = await self.get(owner_id, project_id, campaign_id)
        if campaign is None:
            return None
        metrics = await self.compute_metrics(owner_id, project_id, campaign_id)
        if metrics is None:
            return None

        plans = await self._plans.list_by_project(owner_id, project_id, limit=200)
        linked_plans = [
            plan for plan in plans if campaign_id_in_context(plan.project_context, campaign_id)
        ]
        latest_plan_status = linked_plans[0].status.value if linked_plans else None

        latest_execution_status = None
        if linked_plans:
            runs = await self._runs.list_by_project(
                owner_id,
                project_id,
                marketing_plan_id=linked_plans[0].id,
                limit=1,
            )
            if runs:
                latest_execution_status = runs[0].status.value

        return CampaignDashboard(
            campaign=campaign_to_contract(campaign),
            metrics=metrics,
            latest_plan_status=latest_plan_status,
            latest_execution_status=latest_execution_status,
        )

    @staticmethod
    def tag_context(context: dict[str, Any] | None, campaign_id: UUID) -> dict[str, Any]:
        merged = dict(context or {})
        merged["source_campaign_id"] = str(campaign_id)
        return merged

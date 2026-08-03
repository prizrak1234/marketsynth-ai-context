"""Campaign plan draft service — planning artifact only, no assets/jobs (Phase 10.1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.campaign_plan_drafts import CampaignPlanDraftTable
from app.db.repositories.campaign_plan_drafts import CampaignPlanDraftRepository
from app.db.repositories.marketing_campaigns import MarketingCampaignRepository
from app.marketing.contracts import CampaignPlanDraftStatus, MarketingCampaignStatus
from app.marketing.plan_draft_asset_mapping import (
    PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS,
    PLAN_DRAFT_GENERATION_PARTIAL_STATE,
    plan_draft_assets_cover_all_items,
)
from app.marketing.plan_payload_validation import (
    CampaignPlanContentItem,
    CampaignPlanPayloadShape,
    validate_and_normalize_plan_payload,
)
from app.services.agent_runs import AgentRunService
from app.services.content_asset_service import ContentAssetService
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class PlanDraftGenerateAssetsResult(BaseModel):
    created_count: int
    asset_ids: list[UUID]
    already_generated: bool = False


class CampaignPlanDraftService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CampaignPlanDraftRepository(session)
        self._campaigns = MarketingCampaignRepository(session)
        self._projects = ProjectService(session)
        self._agent_runs = AgentRunService(session)
        self._content_assets = ContentAssetService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _get_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ):
        return await self._campaigns.get_by_id_for_project(campaign_id, owner_id, project_id)

    async def _validate_source_agent_run(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_agent_run_id: UUID | None,
    ) -> bool:
        if source_agent_run_id is None:
            return True
        run = await self._agent_runs.get_run(owner_id, source_agent_run_id)
        return run is not None and run.project_id == project_id

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        title: str,
        plan_payload: dict[str, Any],
        source_agent_run_id: UUID | None = None,
    ) -> CampaignPlanDraftTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        campaign = await self._get_campaign(owner_id, project_id, campaign_id)
        if campaign is None:
            return None
        if campaign.status == MarketingCampaignStatus.ARCHIVED:
            raise InvalidStateError("Cannot create plan drafts for archived campaigns")

        if not await self._validate_source_agent_run(owner_id, project_id, source_agent_run_id):
            return None

        normalized_payload = validate_and_normalize_plan_payload(plan_payload)

        row = CampaignPlanDraftTable(
            owner_id=owner_id,
            project_id=project_id,
            campaign_id=campaign_id,
            source_agent_run_id=source_agent_run_id,
            title=sanitize_text(title)[:512],
            plan_payload=normalized_payload,
            status=CampaignPlanDraftStatus.DRAFT,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def list_by_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[CampaignPlanDraftTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        campaign = await self._get_campaign(owner_id, project_id, campaign_id)
        if campaign is None:
            return None
        return await self._repo.list_by_campaign(
            owner_id,
            project_id,
            campaign_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        draft_id: UUID,
    ) -> CampaignPlanDraftTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        campaign = await self._get_campaign(owner_id, project_id, campaign_id)
        if campaign is None:
            return None
        return await self._repo.get_by_id_for_campaign(
            draft_id,
            owner_id,
            project_id,
            campaign_id,
        )

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        draft_id: UUID,
    ) -> CampaignPlanDraftTable | None:
        row = await self.get(owner_id, project_id, campaign_id, draft_id)
        if row is None:
            return None
        if row.status == CampaignPlanDraftStatus.ARCHIVED:
            raise InvalidStateError("Campaign plan draft is already archived")

        async with transactional(self._session):
            row.updated_at = utc_now()
            return await self._repo.archive(row)

    def _parse_content_items(self, plan_payload: dict[str, Any]) -> list[CampaignPlanContentItem]:
        try:
            shape = CampaignPlanPayloadShape.model_validate(plan_payload)
        except ValidationError as exc:
            raise InvalidStateError("Invalid plan_payload content_items") from exc
        return shape.content_items

    async def generate_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        draft_id: UUID,
    ) -> PlanDraftGenerateAssetsResult | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        campaign = await self._get_campaign(owner_id, project_id, campaign_id)
        if campaign is None:
            return None
        if campaign.status == MarketingCampaignStatus.ARCHIVED:
            raise InvalidStateError("Cannot generate assets for archived campaigns")

        row = await self._repo.get_by_id_for_campaign(
            draft_id,
            owner_id,
            project_id,
            campaign_id,
        )
        if row is None:
            return None
        if row.status == CampaignPlanDraftStatus.ARCHIVED:
            raise InvalidStateError("Cannot generate assets from archived plan draft")

        content_items = self._parse_content_items(dict(row.plan_payload or {}))
        if not content_items:
            raise InvalidStateError("Plan draft has no content_items")
        if len(content_items) > PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS:
            raise InvalidStateError(
                "Plan draft content_items exceeds maximum of "
                f"{PLAN_DRAFT_GENERATE_ASSETS_MAX_ITEMS} items",
            )

        expected_count = len(content_items)

        async with transactional(self._session):
            existing = await self._content_assets.list_drafts_for_plan_draft(
                owner_id,
                project_id,
                campaign_id,
                row.id,
            )
            existing_count = len(existing)

            if existing_count == 0:
                created = await self._content_assets.create_drafts_from_plan_items_in_session(
                    owner_id,
                    project_id,
                    campaign_id=campaign_id,
                    brief_id=campaign.brief_id,
                    draft_id=row.id,
                    content_items=content_items,
                )
                return PlanDraftGenerateAssetsResult(
                    created_count=len(created),
                    asset_ids=[asset.id for asset in created],
                    already_generated=False,
                )

            if existing_count == expected_count and plan_draft_assets_cover_all_items(
                existing,
                expected_count=expected_count,
            ):
                return PlanDraftGenerateAssetsResult(
                    created_count=0,
                    asset_ids=[asset.id for asset in existing],
                    already_generated=True,
                )

            raise InvalidStateError(PLAN_DRAFT_GENERATION_PARTIAL_STATE)

"""Campaign brief persistence and provenance (Phase AI.211–AI.213)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.campaign_brief import CampaignBriefTable
from app.db.repositories.campaign_briefs import CampaignBriefRepository
from app.domain.campaign_brief_completeness import evaluate_brief_completeness
from app.domain.campaign_brief_draft import merge_brief_answers
from app.schemas.contracts import (
    BusinessIntent,
    CampaignBrief,
    CampaignBriefFields,
    CampaignBriefStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_TEXT_MAX = 4096
_NAME_MAX = 256


class CampaignBriefService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._briefs = CampaignBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _sanitize_fields(brief: CampaignBriefFields) -> CampaignBriefFields:
        data = brief.model_dump()
        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = sanitize_text(value).strip()[:_TEXT_MAX] or None
            elif isinstance(value, list):
                data[key] = [
                    sanitize_text(item).strip()[:128]
                    for item in value
                    if str(item).strip()
                ]
        if isinstance(data.get("business_name"), str):
            data["business_name"] = data["business_name"][:_NAME_MAX]
        return CampaignBriefFields.model_validate(data)

    @staticmethod
    def _intent_payload(intent: BusinessIntent) -> dict[str, Any]:
        return sanitize_payload(intent.model_dump(mode="json")) or {}

    def complete_brief(
        self,
        *,
        intent: BusinessIntent,
        scenario_id: str,
        brief: CampaignBriefFields,
        answers: dict[str, str] | None = None,
    ) -> tuple[CampaignBriefFields, Any]:
        merged = merge_brief_answers(brief, answers or {})
        sanitized = self._sanitize_fields(merged)
        completeness = evaluate_brief_completeness(sanitized)
        return sanitized, completeness

    async def confirm_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        intent: BusinessIntent,
        scenario_id: str,
        brief: CampaignBriefFields,
    ) -> CampaignBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        sanitized, completeness = self.complete_brief(
            intent=intent,
            scenario_id=scenario_id,
            brief=brief,
        )
        if not completeness.passed:
            raise InvalidStateError("campaign_brief_completeness_gate")

        row = CampaignBriefTable(
            owner_id=owner_id,
            project_id=project_id,
            source_intent=self._intent_payload(intent),
            source_scenario_id=scenario_id,
            status=CampaignBriefStatus.CONFIRMED,
            business_name=sanitized.business_name,
            industry=sanitized.industry,
            offer=sanitized.offer,
            target_audience=sanitized.target_audience,
            geography=sanitized.geography,
            channels=sanitized.channels,
            budget_range=sanitized.budget_range,
            deadline=sanitized.deadline,
            constraints=sanitized.constraints,
            success_metric=sanitized.success_metric,
            goal=sanitized.goal,
            completeness_score=completeness.score,
        )
        async with transactional(self._session):
            return await self._briefs.create(row)

    async def get_confirmed_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> CampaignBriefTable | None:
        row = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if row is None or row.status != CampaignBriefStatus.CONFIRMED:
            return None
        return row

    async def link_to_campaign(
        self,
        row: CampaignBriefTable,
        campaign_id: UUID,
    ) -> CampaignBriefTable:
        row.campaign_id = campaign_id
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._briefs.update(row)

    async def safe_summary_for_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> dict[str, Any] | None:
        row = await self._briefs.get_confirmed_for_campaign(campaign_id, owner_id, project_id)
        if row is None:
            return None
        return self.build_safe_summary(row)

    @staticmethod
    def build_safe_summary(row: CampaignBriefTable) -> dict[str, Any]:
        payload = {
            "brief_id": str(row.id),
            "industry": row.industry,
            "offer": row.offer,
            "target_audience": row.target_audience,
            "goal": row.goal,
            "geography": row.geography,
            "channels": row.channels,
            "budget_range": row.budget_range,
            "deadline": row.deadline,
            "success_metric": row.success_metric,
            "business_name": row.business_name,
        }
        return sanitize_payload(payload) or {}

    async def get_by_id(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> CampaignBriefTable | None:
        return await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)


def campaign_brief_to_contract(row: CampaignBriefTable) -> CampaignBrief:
    return CampaignBrief(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        campaign_id=row.campaign_id,
        source_intent=dict(row.source_intent or {}),
        source_scenario_id=row.source_scenario_id,
        status=CampaignBriefStatus(row.status),
        business_name=row.business_name,
        industry=row.industry,
        offer=row.offer,
        target_audience=row.target_audience,
        geography=row.geography,
        channels=list(row.channels or []),
        budget_range=row.budget_range,
        deadline=row.deadline,
        constraints=row.constraints,
        success_metric=row.success_metric,
        goal=row.goal,
        completeness_score=row.completeness_score,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

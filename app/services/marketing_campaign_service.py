"""Marketing campaign service — CRUD skeleton without AI logic (Phase 9.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.base import utc_now
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.db.repositories.marketing_campaigns import MarketingCampaignRepository
from app.marketing.contracts import MarketingCampaignStatus
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_CAMPAIGN_UPDATE_FIELDS = frozenset(
    {
        "brief_id",
        "title",
        "description",
        "status",
        "start_at",
        "end_at",
        "campaign_metadata",
    },
)


def _normalize_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # DBs like SQLite may return naive datetimes; interpret them as UTC.
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class MarketingCampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarketingCampaignRepository(session)
        self._briefs = MarketingBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _validate_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID | None,
    ) -> bool:
        if brief_id is None:
            return True
        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        return brief is not None

    def _assert_not_archived(self, row: MarketingCampaignTable) -> None:
        if row.status == MarketingCampaignStatus.ARCHIVED:
            raise InvalidStateError("Archived campaigns cannot be modified")

    @staticmethod
    def _assert_time_bounds(start_at: datetime | None, end_at: datetime | None) -> None:
        if start_at is not None and end_at is not None and end_at <= start_at:
            raise InvalidStateError("end_at must be greater than start_at")

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        brief_id: UUID | None,
        title: str,
        description: str | None,
        status: MarketingCampaignStatus = MarketingCampaignStatus.DRAFT,
        start_at: datetime | None,
        end_at: datetime | None,
        campaign_metadata: dict[str, Any] | None,
    ) -> MarketingCampaignTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if not await self._validate_brief(owner_id, project_id, brief_id):
            return None

        start_at = _normalize_aware_utc(start_at)
        end_at = _normalize_aware_utc(end_at)
        self._assert_time_bounds(start_at, end_at)

        row = MarketingCampaignTable(
            owner_id=owner_id,
            project_id=project_id,
            brief_id=brief_id,
            title=sanitize_text(title)[:512],
            description=sanitize_text(description)[:4096] if description else None,
            status=status,
            start_at=start_at,
            end_at=end_at,
            campaign_metadata=sanitize_payload(campaign_metadata or {}) or {},
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MarketingCampaignTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> MarketingCampaignTable | None:
        return await self._repo.get_by_id_for_project(campaign_id, owner_id, project_id)

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        updates: dict[str, Any],
    ) -> MarketingCampaignTable | None:
        row = await self.get(owner_id, project_id, campaign_id)
        if row is None:
            return None
        self._assert_not_archived(row)

        filtered: dict[str, Any] = {}
        for key, value in updates.items():
            if key in _CAMPAIGN_UPDATE_FIELDS:
                filtered[key] = value

        if not filtered:
            return row

        if "brief_id" in filtered and not await self._validate_brief(
            owner_id,
            project_id,
            filtered["brief_id"],
        ):
            return None

        if "status" in filtered and filtered["status"] == MarketingCampaignStatus.ARCHIVED:
            raise InvalidStateError("Use archive endpoint to archive a campaign")

        # Normalize datetimes and validate combined bounds against existing values.
        next_start = _normalize_aware_utc(filtered.get("start_at", row.start_at))
        next_end = _normalize_aware_utc(filtered.get("end_at", row.end_at))
        self._assert_time_bounds(next_start, next_end)

        if "title" in filtered and isinstance(filtered["title"], str):
            filtered["title"] = sanitize_text(filtered["title"])[:512]
        if "description" in filtered and isinstance(filtered["description"], str):
            filtered["description"] = sanitize_text(filtered["description"])[:4096]
        if "campaign_metadata" in filtered:
            filtered["campaign_metadata"] = sanitize_payload(filtered["campaign_metadata"]) or {}

        filtered["start_at"] = next_start
        filtered["end_at"] = next_end

        async with transactional(self._session):
            for key, value in filtered.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            return await self._repo.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> MarketingCampaignTable | None:
        row = await self.get(owner_id, project_id, campaign_id)
        if row is None:
            return None
        if row.status == MarketingCampaignStatus.ARCHIVED:
            raise InvalidStateError("Marketing campaign is already archived")

        async with transactional(self._session):
            row.updated_at = utc_now()
            return await self._repo.archive(row)


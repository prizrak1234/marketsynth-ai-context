"""Marketing brief service — CRUD without LLM or graph (Phase 4.0)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import MarketingBriefTable
from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.marketing.contracts import MarketingBriefStatus
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_BRIEF_UPDATE_FIELDS = frozenset(
    {
        "title",
        "product_description",
        "target_audience",
        "offer",
        "goals",
        "constraints",
        "status",
    },
)


class MarketingBriefService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarketingBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        title: str,
        product_description: str = "",
        target_audience: str = "",
        offer: str = "",
        goals: list[str] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> MarketingBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        row = MarketingBriefTable(
            owner_id=owner_id,
            project_id=project_id,
            title=title,
            product_description=product_description,
            target_audience=target_audience,
            offer=offer,
            goals=goals or [],
            constraints=constraints or {},
            status=MarketingBriefStatus.DRAFT,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MarketingBriefTable | None:
        return await self._repo.get_by_id_for_owner(brief_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MarketingBriefTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        updates: dict[str, Any],
    ) -> MarketingBriefTable | None:
        row = await self.get(owner_id, project_id, brief_id)
        if row is None:
            return None

        filtered = {key: value for key, value in updates.items() if key in _BRIEF_UPDATE_FIELDS}
        if not filtered:
            return row

        if filtered.get("status") == MarketingBriefStatus.ARCHIVED:
            filtered.pop("status", None)

        for key, value in filtered.items():
            setattr(row, key, value)

        async with transactional(self._session):
            return await self._repo.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MarketingBriefTable | None:
        row = await self.get(owner_id, project_id, brief_id)
        if row is None:
            return None
        async with transactional(self._session):
            return await self._repo.archive(row)

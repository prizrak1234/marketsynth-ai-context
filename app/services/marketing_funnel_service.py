"""Marketing funnel service — CRUD without LLM or graph (Phase 4.8)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.models.marketing_funnels import (
    FunnelStepAssetLinkTable,
    MarketingFunnelStepTable,
    MarketingFunnelTable,
)
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.funnel_step_asset_links import (
    FunnelStepAssetLinkRepository,
    FunnelStepAssetLinkRow,
)
from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.db.repositories.marketing_funnel_steps import MarketingFunnelStepRepository
from app.db.repositories.marketing_funnels import MarketingFunnelRepository
from app.marketing.funnel_contracts import (
    FunnelStepAssetRole,
    FunnelStepStatus,
    FunnelStepType,
    MarketingFunnelStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_FUNNEL_UPDATE_FIELDS = frozenset(
    {"title", "description", "funnel_metadata", "status", "brief_id"},
)
_STEP_UPDATE_FIELDS = frozenset(
    {"title", "description", "step_type", "position", "step_metadata", "status"},
)


class MarketingFunnelService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._funnels = MarketingFunnelRepository(session)
        self._steps = MarketingFunnelStepRepository(session)
        self._links = FunnelStepAssetLinkRepository(session)
        self._briefs = MarketingBriefRepository(session)
        self._assets = ContentAssetRepository(session)
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

    def _assert_funnel_accepts_steps(self, funnel: MarketingFunnelTable) -> None:
        if funnel.status == MarketingFunnelStatus.ARCHIVED:
            raise InvalidStateError("Archived funnels cannot receive new steps")

    def _assert_step_accepts_links(self, step: MarketingFunnelStepTable) -> None:
        if step.status == FunnelStepStatus.ARCHIVED:
            raise InvalidStateError("Archived funnel steps cannot receive asset links")

    async def create_funnel(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        title: str,
        description: str = "",
        brief_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarketingFunnelTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        if not await self._validate_brief(owner_id, project_id, brief_id):
            return None

        row = MarketingFunnelTable(
            owner_id=owner_id,
            project_id=project_id,
            brief_id=brief_id,
            title=title,
            description=description,
            funnel_metadata=metadata or {},
            status=MarketingFunnelStatus.DRAFT,
        )
        async with transactional(self._session):
            return await self._funnels.create(row)

    async def list_funnels(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MarketingFunnelTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._funnels.list_by_project(
            owner_id,
            project_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def get_funnel(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
    ) -> MarketingFunnelTable | None:
        return await self._funnels.get_by_id_for_project(funnel_id, owner_id, project_id)

    async def update_funnel(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        updates: dict[str, Any],
    ) -> MarketingFunnelTable | None:
        row = await self.get_funnel(owner_id, project_id, funnel_id)
        if row is None:
            return None

        filtered: dict[str, Any] = {}
        for key, value in updates.items():
            if key == "metadata":
                filtered["funnel_metadata"] = value
            elif key in _FUNNEL_UPDATE_FIELDS:
                filtered[key] = value

        if "brief_id" in filtered and not await self._validate_brief(
            owner_id,
            project_id,
            filtered["brief_id"],
        ):
            return None

        if not filtered:
            return row

        if filtered.get("status") == MarketingFunnelStatus.ARCHIVED:
            filtered.pop("status", None)

        for key, value in filtered.items():
            setattr(row, key, value)

        async with transactional(self._session):
            return await self._funnels.update(row)

    async def archive_funnel(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
    ) -> MarketingFunnelTable | None:
        row = await self.get_funnel(owner_id, project_id, funnel_id)
        if row is None:
            return None
        if row.status == MarketingFunnelStatus.ARCHIVED:
            raise InvalidStateError("Marketing funnel is already archived")

        async with transactional(self._session):
            return await self._funnels.archive(row)

    async def create_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        *,
        step_type: FunnelStepType,
        title: str,
        description: str = "",
        position: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarketingFunnelStepTable | None:
        funnel = await self.get_funnel(owner_id, project_id, funnel_id)
        if funnel is None:
            return None

        self._assert_funnel_accepts_steps(funnel)

        if position is None:
            position = await self._steps.max_position(funnel_id, owner_id, project_id) + 1

        row = MarketingFunnelStepTable(
            owner_id=owner_id,
            project_id=project_id,
            funnel_id=funnel_id,
            step_type=step_type,
            title=title,
            description=description,
            position=position,
            step_metadata=metadata or {},
            status=FunnelStepStatus.DRAFT,
        )
        try:
            async with transactional(self._session):
                return await self._steps.create(row)
        except IntegrityError as exc:
            raise InvalidStateError(
                "Funnel step position must be unique within the funnel",
            ) from exc

    async def list_steps(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[MarketingFunnelStepTable] | None:
        if await self.get_funnel(owner_id, project_id, funnel_id) is None:
            return None
        return await self._steps.list_by_funnel(
            funnel_id,
            owner_id,
            project_id,
            include_archived=include_archived,
        )

    async def update_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_id: UUID,
        updates: dict[str, Any],
    ) -> MarketingFunnelStepTable | None:
        row = await self._steps.get_by_id_for_funnel(
            step_id,
            funnel_id,
            owner_id,
            project_id,
        )
        if row is None:
            return None

        filtered: dict[str, Any] = {}
        for key, value in updates.items():
            if key == "metadata":
                filtered["step_metadata"] = value
            elif key in _STEP_UPDATE_FIELDS:
                filtered[key] = value

        if not filtered:
            return row

        if filtered.get("status") == FunnelStepStatus.ARCHIVED:
            filtered.pop("status", None)

        for key, value in filtered.items():
            setattr(row, key, value)

        try:
            async with transactional(self._session):
                return await self._steps.update(row)
        except IntegrityError as exc:
            raise InvalidStateError(
                "Funnel step position must be unique within the funnel",
            ) from exc

    async def archive_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_id: UUID,
    ) -> MarketingFunnelStepTable | None:
        row = await self._steps.get_by_id_for_funnel(
            step_id,
            funnel_id,
            owner_id,
            project_id,
        )
        if row is None:
            return None
        if row.status == FunnelStepStatus.ARCHIVED:
            raise InvalidStateError("Funnel step is already archived")

        async with transactional(self._session):
            return await self._steps.archive(row)

    async def reorder_steps(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_ids: list[UUID],
    ) -> list[MarketingFunnelStepTable] | None:
        if await self.get_funnel(owner_id, project_id, funnel_id) is None:
            return None

        steps = await self._steps.list_by_funnel(
            funnel_id,
            owner_id,
            project_id,
            include_archived=True,
        )
        step_map = {step.id: step for step in steps}
        if set(step_ids) != set(step_map):
            raise InvalidStateError("Reorder must include every step in the funnel exactly once")

        async with transactional(self._session):
            offset = len(step_ids) + 1
            for index, step_id in enumerate(step_ids):
                step = step_map[step_id]
                step.position = offset + index
                await self._steps.update(step)
            for index, step_id in enumerate(step_ids, start=1):
                step = step_map[step_id]
                step.position = index
                await self._steps.update(step)

        return await self._steps.list_by_funnel(
            funnel_id,
            owner_id,
            project_id,
            include_archived=True,
        )

    async def link_asset_to_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_id: UUID,
        asset_id: UUID,
        *,
        role: FunnelStepAssetRole = FunnelStepAssetRole.PRIMARY,
    ) -> FunnelStepAssetLinkTable | None:
        funnel = await self.get_funnel(owner_id, project_id, funnel_id)
        if funnel is None:
            return None

        step = await self._steps.get_by_id_for_funnel(
            step_id,
            funnel_id,
            owner_id,
            project_id,
        )
        if step is None:
            return None

        self._assert_step_accepts_links(step)

        asset = await self._assets.get_by_id_for_owner(asset_id, owner_id, project_id)
        if asset is None:
            return None

        row = FunnelStepAssetLinkTable(
            owner_id=owner_id,
            project_id=project_id,
            funnel_id=funnel_id,
            step_id=step_id,
            asset_id=asset_id,
            role=role,
        )
        async with transactional(self._session):
            return await self._links.create(row)

    async def unlink_asset_from_step(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_id: UUID,
        asset_id: UUID,
    ) -> bool:
        link = await self._links.get_link(
            step_id,
            asset_id,
            funnel_id,
            owner_id,
            project_id,
        )
        if link is None:
            return False

        async with transactional(self._session):
            await self._links.delete(link)
        return True

    async def list_step_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        funnel_id: UUID,
        step_id: UUID,
    ) -> list[FunnelStepAssetLinkRow] | None:
        if await self._steps.get_by_id_for_funnel(
            step_id,
            funnel_id,
            owner_id,
            project_id,
        ) is None:
            return None
        return await self._links.list_by_step(step_id, funnel_id, owner_id, project_id)

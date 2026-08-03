"""Marketing skill run repository (Phase AI.227)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_skill_run import MarketingSkillRunTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import MarketingSkillType


class MarketingSkillRunRepository(BaseRepository[MarketingSkillRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingSkillRunTable)

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingSkillRunTable | None:
        statement = select(MarketingSkillRunTable).where(
            MarketingSkillRunTable.id == run_id,
            MarketingSkillRunTable.owner_id == owner_id,
            MarketingSkillRunTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID | None = None,
        skill_type: MarketingSkillType | None = None,
        limit: int = 50,
    ) -> list[MarketingSkillRunTable]:
        statement = (
            select(MarketingSkillRunTable)
            .where(
                MarketingSkillRunTable.owner_id == owner_id,
                MarketingSkillRunTable.project_id == project_id,
            )
            .order_by(MarketingSkillRunTable.created_at.desc())
            .limit(limit)
        )
        if campaign_id is not None:
            statement = statement.where(MarketingSkillRunTable.campaign_id == campaign_id)
        if skill_type is not None:
            statement = statement.where(MarketingSkillRunTable.skill_type == skill_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

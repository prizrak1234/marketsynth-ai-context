"""Marketing tool call repository (Phase AI.217)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_tool_call import MarketingToolCallTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import MarketingToolType


class MarketingToolCallRepository(BaseRepository[MarketingToolCallTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingToolCallTable)

    async def get_by_id_for_owner(
        self,
        call_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingToolCallTable | None:
        statement = select(MarketingToolCallTable).where(
            MarketingToolCallTable.id == call_id,
            MarketingToolCallTable.owner_id == owner_id,
            MarketingToolCallTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        tool_type: MarketingToolType | None = None,
        limit: int = 50,
    ) -> list[MarketingToolCallTable]:
        statement = (
            select(MarketingToolCallTable)
            .where(
                MarketingToolCallTable.owner_id == owner_id,
                MarketingToolCallTable.project_id == project_id,
            )
            .order_by(MarketingToolCallTable.created_at.desc())
            .limit(limit)
        )
        if tool_type is not None:
            statement = statement.where(MarketingToolCallTable.tool_type == tool_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

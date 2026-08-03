"""Marketing specialist output version repository (Phase AI.30)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_specialist_output import MarketingSpecialistOutputVersionTable
from app.db.repositories.base import BaseRepository


class MarketingSpecialistOutputVersionRepository(
    BaseRepository[MarketingSpecialistOutputVersionTable],
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingSpecialistOutputVersionTable)

    async def list_for_output(
        self,
        specialist_output_id: UUID,
        *,
        limit: int = 100,
    ) -> list[MarketingSpecialistOutputVersionTable]:
        statement = (
            select(MarketingSpecialistOutputVersionTable)
            .where(
                MarketingSpecialistOutputVersionTable.specialist_output_id
                == specialist_output_id,
            )
            .order_by(MarketingSpecialistOutputVersionTable.version_number.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_version(
        self,
        specialist_output_id: UUID,
        version_number: int,
    ) -> MarketingSpecialistOutputVersionTable | None:
        statement = select(MarketingSpecialistOutputVersionTable).where(
            MarketingSpecialistOutputVersionTable.specialist_output_id
            == specialist_output_id,
            MarketingSpecialistOutputVersionTable.version_number == version_number,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

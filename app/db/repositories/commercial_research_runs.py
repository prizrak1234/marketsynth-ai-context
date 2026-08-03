"""CommercialResearchRun repository (Phase 1B.1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.commercial_research_run import CommercialResearchRunTable
from app.db.repositories.base import BaseRepository


class CommercialResearchRunRepository(BaseRepository[CommercialResearchRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CommercialResearchRunTable)

    async def get_by_request_hash(
        self,
        owner_id: UUID,
        user_request_id: UUID,
        request_hash: str,
    ) -> CommercialResearchRunTable | None:
        statement = select(CommercialResearchRunTable).where(
            CommercialResearchRunTable.owner_id == owner_id,
            CommercialResearchRunTable.user_request_id == user_request_id,
            CommercialResearchRunTable.request_hash == request_hash,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        owner_id: UUID,
        idempotency_key: str,
    ) -> CommercialResearchRunTable | None:
        statement = select(CommercialResearchRunTable).where(
            CommercialResearchRunTable.owner_id == owner_id,
            CommercialResearchRunTable.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_for_user_request(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> CommercialResearchRunTable | None:
        statement = (
            select(CommercialResearchRunTable)
            .where(
                CommercialResearchRunTable.owner_id == owner_id,
                CommercialResearchRunTable.user_request_id == user_request_id,
            )
            .order_by(desc(CommercialResearchRunTable.run_version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def max_run_version(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> int:
        statement = select(CommercialResearchRunTable.run_version).where(
            CommercialResearchRunTable.owner_id == owner_id,
            CommercialResearchRunTable.user_request_id == user_request_id,
        )
        result = await self.session.execute(statement)
        versions = list(result.scalars().all())
        return max(versions) if versions else 0

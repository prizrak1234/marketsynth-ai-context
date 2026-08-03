"""API key repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.api_key import ApiKeyTable
from app.db.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKeyTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApiKeyTable)

    async def get_by_prefix(self, key_prefix: str) -> ApiKeyTable | None:
        statement = select(ApiKeyTable).where(ApiKeyTable.key_prefix == key_prefix)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[ApiKeyTable]:
        statement = (
            select(ApiKeyTable)
            .where(ApiKeyTable.user_id == user_id)
            .order_by(ApiKeyTable.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_user(self, api_key_id: UUID, user_id: UUID) -> ApiKeyTable | None:
        statement = select(ApiKeyTable).where(
            ApiKeyTable.id == api_key_id,
            ApiKeyTable.user_id == user_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

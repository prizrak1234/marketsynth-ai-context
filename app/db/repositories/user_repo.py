"""User repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.user import UserTable
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserTable)

    async def get_by_telegram_id(self, telegram_id: int) -> UserTable | None:
        statement = select(UserTable).where(UserTable.telegram_id == telegram_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

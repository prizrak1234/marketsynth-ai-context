"""User business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.core.config import get_settings
from app.schemas.contracts import BetaAccessStatus
from app.schemas.crud import UserCreate, UserUpdate
from app.services.transaction import transactional


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def create(self, data: UserCreate) -> UserTable:
        payload = data.model_dump()
        settings = get_settings()
        if settings.is_development or settings.app_env == "test":
            payload["beta_access_status"] = BetaAccessStatus.APPROVED
        async with transactional(self._session):
            row = UserTable(**payload)
            return await self._repo.create(row)

    async def get_by_id(self, user_id: UUID) -> UserTable | None:
        return await self._repo.get_by_id(user_id)

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[UserTable]:
        return await self._repo.list(offset=offset, limit=limit)

    async def update(self, user_id: UUID, data: UserUpdate) -> UserTable | None:
        row = await self._repo.get_by_id(user_id)
        if row is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row

        async with transactional(self._session):
            for field, value in updates.items():
                setattr(row, field, value)
            row.updated_at = utc_now()
            return await self._repo.update(row)

    async def delete(self, user_id: UUID) -> bool:
        row = await self._repo.get_by_id(user_id)
        if row is None:
            return False
        async with transactional(self._session):
            await self._repo.delete(row)
        return True

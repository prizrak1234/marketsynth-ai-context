"""Browser session repository (CPH.3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.browser_session import BrowserSessionTable
from app.db.base import utc_now


class BrowserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: BrowserSessionTable) -> BrowserSessionTable:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_token_hash(self, token_hash: str) -> BrowserSessionTable | None:
        result = await self._session.execute(
            select(BrowserSessionTable).where(BrowserSessionTable.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self, session_id: UUID, user_id: UUID
    ) -> BrowserSessionTable | None:
        result = await self._session.execute(
            select(BrowserSessionTable).where(
                BrowserSessionTable.id == session_id,
                BrowserSessionTable.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID, *, limit: int = 50) -> list[BrowserSessionTable]:
        result = await self._session.execute(
            select(BrowserSessionTable)
            .where(BrowserSessionTable.user_id == user_id)
            .order_by(BrowserSessionTable.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, row: BrowserSessionTable) -> BrowserSessionTable:
        row.last_seen_at = utc_now()
        self._session.add(row)
        await self._session.flush()
        return row

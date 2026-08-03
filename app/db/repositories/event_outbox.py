"""Event outbox repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.db.base import utc_now
from app.db.models.event_outbox import EventOutboxTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import EventOutboxStatus, EventType


class EventOutboxRepository(BaseRepository[EventOutboxTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventOutboxTable)

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        event_type: EventType | None = None,
        status: EventOutboxStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventOutboxTable]:
        statement = select(EventOutboxTable).where(
            EventOutboxTable.project_id == project_id,
            EventOutboxTable.owner_id == owner_id,
        )
        if event_type is not None:
            statement = statement.where(EventOutboxTable.event_type == event_type)
        if status is not None:
            statement = statement.where(EventOutboxTable.status == status)
        statement = (
            statement.order_by(EventOutboxTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_pending(
        self,
        *,
        limit: int = 50,
        project_id: UUID | None = None,
    ) -> list[EventOutboxTable]:
        statement = select(EventOutboxTable).where(
            EventOutboxTable.status == EventOutboxStatus.PENDING,
        )
        if project_id is not None:
            statement = statement.where(EventOutboxTable.project_id == project_id)
        statement = statement.order_by(EventOutboxTable.created_at.asc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def mark_sent(self, row: EventOutboxTable) -> EventOutboxTable:
        row.status = EventOutboxStatus.SENT
        row.last_error = None
        row.updated_at = utc_now()
        return await self.update(row)

    async def get_for_project(
        self,
        event_id: UUID,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> EventOutboxTable | None:
        statement = select(EventOutboxTable).where(
            EventOutboxTable.id == event_id,
            EventOutboxTable.owner_id == owner_id,
            EventOutboxTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def reset_for_replay(self, row: EventOutboxTable) -> EventOutboxTable:
        row.status = EventOutboxStatus.PENDING
        row.attempts = 0
        row.last_error = None
        row.updated_at = utc_now()
        return await self.update(row)

    async def record_delivery_failure(
        self,
        row: EventOutboxTable,
        *,
        error: str,
        max_attempts: int,
    ) -> EventOutboxTable:
        row.attempts += 1
        row.last_error = error[:500]
        row.updated_at = utc_now()
        if row.attempts >= max_attempts:
            row.status = EventOutboxStatus.DEAD_LETTERED
        return await self.update(row)

    async def list_for_batch_replay(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        statuses: list[EventOutboxStatus],
        event_type: EventType | None = None,
        limit: int = 50,
    ) -> list[EventOutboxTable]:
        statement = select(EventOutboxTable).where(
            EventOutboxTable.project_id == project_id,
            EventOutboxTable.owner_id == owner_id,
            col(EventOutboxTable.status).in_(statuses),
        )
        if event_type is not None:
            statement = statement.where(EventOutboxTable.event_type == event_type)
        statement = statement.order_by(EventOutboxTable.created_at.asc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def mark_dead_lettered(self, row: EventOutboxTable, *, error: str) -> EventOutboxTable:
        row.status = EventOutboxStatus.DEAD_LETTERED
        row.last_error = error[:500]
        row.updated_at = utc_now()
        return await self.update(row)

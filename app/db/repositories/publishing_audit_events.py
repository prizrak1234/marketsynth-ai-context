"""Publishing audit event persistence (Phase AI.64)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publishing_audit_event import PublishingAuditEventTable
from app.publishing_foundation.contracts import PublishingAuditEventType


class PublishingAuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: PublishingAuditEventTable) -> PublishingAuditEventTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        event_type: PublishingAuditEventType | None = None,
        limit: int = 100,
    ) -> list[PublishingAuditEventTable]:
        statement = select(PublishingAuditEventTable).where(
            PublishingAuditEventTable.owner_id == owner_id,
            PublishingAuditEventTable.project_id == project_id,
        )
        if event_type is not None:
            statement = statement.where(
                PublishingAuditEventTable.event_type == event_type,
            )
        statement = (
            statement.order_by(PublishingAuditEventTable.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_by_event_type(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> dict[str, int]:
        statement = (
            select(PublishingAuditEventTable.event_type, func.count())
            .where(
                PublishingAuditEventTable.owner_id == owner_id,
                PublishingAuditEventTable.project_id == project_id,
            )
            .group_by(PublishingAuditEventTable.event_type)
        )
        result = await self.session.execute(statement)
        return {row[0].value: int(row[1]) for row in result.all()}

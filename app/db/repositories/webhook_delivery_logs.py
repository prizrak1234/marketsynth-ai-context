"""Webhook delivery log repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import WebhookDeliveryLogStatus


class WebhookDeliveryLogRepository(BaseRepository[WebhookDeliveryLogTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WebhookDeliveryLogTable)

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        webhook_id: UUID | None = None,
        event_type: str | None = None,
        status: WebhookDeliveryLogStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookDeliveryLogTable]:
        statement = select(WebhookDeliveryLogTable).where(
            WebhookDeliveryLogTable.project_id == project_id,
            WebhookDeliveryLogTable.owner_id == owner_id,
        )
        if webhook_id is not None:
            statement = statement.where(WebhookDeliveryLogTable.webhook_id == webhook_id)
        if event_type is not None:
            statement = statement.where(WebhookDeliveryLogTable.event_type == event_type)
        if status is not None:
            statement = statement.where(WebhookDeliveryLogTable.status == status)
        statement = (
            statement.order_by(WebhookDeliveryLogTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_older_than(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        created_before: datetime,
    ) -> int:
        statement = delete(WebhookDeliveryLogTable).where(
            WebhookDeliveryLogTable.project_id == project_id,
            WebhookDeliveryLogTable.owner_id == owner_id,
            WebhookDeliveryLogTable.created_at < created_before,
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)

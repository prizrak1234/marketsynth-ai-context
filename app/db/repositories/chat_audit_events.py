"""Chat audit event repository (Phase AI.25)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.chat_audit_event import ChatAuditEventTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import ChatAuditEventType, ChatSessionDomain


class ChatAuditEventRepository(BaseRepository[ChatAuditEventTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatAuditEventTable)

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        session_id: UUID | None = None,
        event_type: ChatAuditEventType | None = None,
        domain: ChatSessionDomain | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatAuditEventTable]:
        statement = select(ChatAuditEventTable).where(
            ChatAuditEventTable.owner_id == owner_id,
            ChatAuditEventTable.project_id == project_id,
        )
        if session_id is not None:
            statement = statement.where(ChatAuditEventTable.session_id == session_id)
        if event_type is not None:
            statement = statement.where(ChatAuditEventTable.event_type == event_type)
        if domain is not None:
            statement = statement.where(ChatAuditEventTable.domain == domain)
        if date_from is not None:
            statement = statement.where(ChatAuditEventTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(ChatAuditEventTable.created_at <= date_to)
        statement = (
            statement.order_by(ChatAuditEventTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_by_event_types(
        self,
        owner_id: UUID,
        project_id: UUID,
        event_types: list[ChatAuditEventType],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        if not event_types:
            return 0
        statement = (
            select(func.count())
            .select_from(ChatAuditEventTable)
            .where(
                ChatAuditEventTable.owner_id == owner_id,
                ChatAuditEventTable.project_id == project_id,
                ChatAuditEventTable.event_type.in_(event_types),
            )
        )
        if date_from is not None:
            statement = statement.where(ChatAuditEventTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(ChatAuditEventTable.created_at <= date_to)
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def count_block_actions_by_type(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        action_events = (
            ChatAuditEventType.BLOCK_ACTION_REQUESTED,
            ChatAuditEventType.BLOCK_ACTION_SUCCEEDED,
            ChatAuditEventType.BLOCK_ACTION_FAILED,
        )
        statement = select(ChatAuditEventTable).where(
            ChatAuditEventTable.owner_id == owner_id,
            ChatAuditEventTable.project_id == project_id,
            ChatAuditEventTable.event_type.in_(action_events),
        )
        if date_from is not None:
            statement = statement.where(ChatAuditEventTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(ChatAuditEventTable.created_at <= date_to)
        result = await self.session.execute(statement)
        counts: dict[str, int] = {}
        for row in result.scalars().all():
            raw_type = row.safe_metadata.get("action_type")
            if raw_type is None:
                continue
            key = str(raw_type)
            counts[key] = counts.get(key, 0) + 1
        return counts

    async def latest_activity_at(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> datetime | None:
        statement = select(func.max(ChatAuditEventTable.created_at)).where(
            ChatAuditEventTable.owner_id == owner_id,
            ChatAuditEventTable.project_id == project_id,
        )
        if date_from is not None:
            statement = statement.where(ChatAuditEventTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(ChatAuditEventTable.created_at <= date_to)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

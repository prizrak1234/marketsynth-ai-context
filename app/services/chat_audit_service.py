"""Chat audit logging (Phase AI.25) — never raises to callers."""

from __future__ import annotations

import structlog
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_audit_event import ChatAuditEventTable
from app.db.repositories.chat_audit_events import ChatAuditEventRepository
from app.schemas.contracts import (
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
)
from app.services.chat_audit_safe_metadata import build_safe_metadata

logger = structlog.get_logger(__name__)


class ChatAuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ChatAuditEventRepository(session)

    async def record(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        event_type: ChatAuditEventType,
        status: str,
        domain: ChatSessionDomain,
        entrypoint: ChatSessionEntrypoint,
        session_id: UUID | None = None,
        message_id: UUID | None = None,
        agent_id: UUID | None = None,
        safe_metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            row = ChatAuditEventTable(
                owner_id=owner_id,
                project_id=project_id,
                session_id=session_id,
                message_id=message_id,
                agent_id=agent_id,
                event_type=event_type,
                domain=domain,
                entrypoint=entrypoint,
                status=status,
                safe_metadata=build_safe_metadata(safe_metadata),
            )
            await self._repo.create(row)
        except Exception:
            logger.warning(
                "chat_audit.record_failed",
                event_type=event_type.value,
                project_id=str(project_id),
                exc_info=True,
            )

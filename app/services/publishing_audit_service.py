"""Publishing audit logging — never raises to callers (Phase AI.64)."""

from __future__ import annotations

import structlog
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publishing_audit_event import PublishingAuditEventTable
from app.db.repositories.publishing_audit_events import PublishingAuditEventRepository
from app.publishing_foundation.contracts import PublishingAuditEventType
from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata

logger = structlog.get_logger(__name__)


class PublishingAuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublishingAuditEventRepository(session)

    async def record(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        event_type: PublishingAuditEventType,
        status: str,
        channel_id: UUID | None = None,
        publication_package_job_id: UUID | None = None,
        safe_metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            row = PublishingAuditEventTable(
                owner_id=owner_id,
                project_id=project_id,
                event_type=event_type,
                status=status,
                channel_id=channel_id,
                publication_package_job_id=publication_package_job_id,
                safe_metadata=sanitize_publishing_metadata(safe_metadata),
            )
            await self._repo.create(row)
        except Exception:
            logger.warning(
                "publishing_audit.record_failed",
                event_type=event_type.value,
                project_id=str(project_id),
                exc_info=True,
            )

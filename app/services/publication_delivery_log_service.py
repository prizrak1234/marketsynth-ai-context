"""Publication delivery log service (Phase 6.1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publication_delivery_log import PublicationDeliveryLogTable
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.publication_delivery_logs import PublicationDeliveryLogRepository
from app.publishing.contracts import PublicationDeliveryLogStatus, PublishingChannelType
from app.publishing.dispatch_result import PublicationDispatchResult
from app.services.transaction import transactional


class PublicationDeliveryLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublicationDeliveryLogRepository(session)
        self._projects = ProjectRepository(session)

    async def record_attempt(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        publication_job_id: UUID,
        channel_id: UUID,
        channel_type: PublishingChannelType,
        attempt_number: int,
        result: PublicationDispatchResult,
    ) -> PublicationDeliveryLogTable:
        row = PublicationDeliveryLogTable(
            owner_id=owner_id,
            project_id=project_id,
            publication_job_id=publication_job_id,
            channel_id=channel_id,
            channel_type=channel_type,
            status=result.status,
            attempt_number=attempt_number,
            duration_ms=result.duration_ms,
            error_code=result.error_code,
            error_message=result.error_message,
            response_preview=result.response_preview,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        job_id: UUID | None = None,
        channel_id: UUID | None = None,
        status: PublicationDeliveryLogStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PublicationDeliveryLogTable] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return await self._repo.list_for_project(
            project_id,
            owner_id=owner_id,
            publication_job_id=job_id,
            channel_id=channel_id,
            status=status,
            limit=limit,
            offset=offset,
        )

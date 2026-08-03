"""Publishing foundation channel registry (Phase AI.60)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.core.security import sanitize_text
from app.db.models.publishing import PublishingChannelTable
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.publishing.contracts import PublishingChannelStatus, PublishingChannelType
from app.publishing_foundation.contracts import (
    PublishingAuditEventType,
    PublishingFoundationChannelStatus,
    PublishingFoundationChannelType,
)
from app.publishing_foundation.channel_config import normalize_foundation_channel_config
from app.schemas.publishing_foundation import (
    PublishingFoundationChannelCreateRequest,
    PublishingFoundationChannelUpdateRequest,
)
from app.services.projects_service import ProjectService
from app.services.publishing_audit_service import PublishingAuditService
from app.services.transaction import transactional

_FOUNDATION_TYPES = frozenset(t.value for t in PublishingFoundationChannelType)


class PublishingFoundationChannelService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublishingChannelRepository(session)
        self._projects = ProjectService(session)
        self._audit = PublishingAuditService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _to_db_channel_type(
        self,
        channel_type: PublishingFoundationChannelType,
    ) -> PublishingChannelType:
        return PublishingChannelType(channel_type.value)

    def _to_db_status(
        self,
        status: PublishingFoundationChannelStatus,
    ) -> PublishingChannelStatus:
        return PublishingChannelStatus(status.value)

    def _assert_foundation_row(self, row: PublishingChannelTable) -> None:
        if row.channel_type.value not in _FOUNDATION_TYPES:
            raise InvalidStateError("Channel is not a publishing foundation channel")

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: PublishingFoundationChannelCreateRequest,
    ) -> PublishingChannelTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        config = normalize_foundation_channel_config(
            body.config_metadata,
            channel_type=body.channel_type.value,
        )
        row = PublishingChannelTable(
            owner_id=owner_id,
            project_id=project_id,
            name=sanitize_text(body.name).strip()[:256],
            channel_type=self._to_db_channel_type(body.channel_type),
            status=self._to_db_status(body.status),
            channel_config=config,
            config_preview={"channel_type": body.channel_type.value},
        )
        async with transactional(self._session):
            created = await self._repo.create(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.CHANNEL_CREATED,
                status="ok",
                channel_id=created.id,
                safe_metadata={
                    "channel_type": body.channel_type.value,
                    "channel_status": body.status.value,
                },
            )
            return created

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
    ) -> PublishingChannelTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._repo.get_for_owner(
            channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if row is None:
            return None
        self._assert_foundation_row(row)
        return row

    async def list(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        channel_type: PublishingFoundationChannelType | None = None,
        status: PublishingFoundationChannelStatus | None = None,
        limit: int = 100,
    ) -> list[PublishingChannelTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        rows = await self._repo.list_for_project(
            project_id,
            owner_id=owner_id,
            include_archived=include_archived,
            channel_type=(
                self._to_db_channel_type(channel_type) if channel_type else None
            ),
            status=self._to_db_status(status) if status else None,
            limit=limit,
        )
        return [row for row in rows if row.channel_type.value in _FOUNDATION_TYPES]

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
        body: PublishingFoundationChannelUpdateRequest,
    ) -> PublishingChannelTable | None:
        row = await self.get(owner_id, project_id, channel_id)
        if row is None:
            return None

        if body.name is not None:
            row.name = sanitize_text(body.name).strip()[:256]
        if body.status is not None:
            row.status = self._to_db_status(body.status)
        if body.config_metadata is not None:
            row.channel_config = normalize_foundation_channel_config(
                body.config_metadata,
                channel_type=row.channel_type.value,
            )
            row.config_preview = {
                "channel_type": row.channel_type.value,
                "updated": True,
            }
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._repo.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
    ) -> PublishingChannelTable | None:
        row = await self.get(owner_id, project_id, channel_id)
        if row is None:
            return None
        if row.status == PublishingChannelStatus.ARCHIVED:
            raise InvalidStateError("Publishing channel is already archived")

        row.status = PublishingChannelStatus.ARCHIVED
        row.updated_at = utc_now()
        async with transactional(self._session):
            updated = await self._repo.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.CHANNEL_ARCHIVED,
                status="ok",
                channel_id=updated.id,
                safe_metadata={"channel_type": updated.channel_type.value},
            )
            return updated

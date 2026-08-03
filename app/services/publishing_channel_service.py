"""Publishing channel service — HTTP-managed destinations (Phase 6.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.publishing import PublishingChannelTable
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.publishing.config_preview import build_config_preview
from app.publishing.contracts import PublishingChannelStatus, PublishingChannelType
from app.publishing.telegram_channel_config import (
    telegram_channel_config_to_dict,
    validate_telegram_channel_config,
)
from app.publishing.webhook_channel_config import (
    validate_webhook_channel_config,
    webhook_channel_config_to_dict,
)
from app.schemas.publishing import (
    PublishingChannelCreateRequest,
    PublishingChannelUpdateRequest,
)
from app.services.transaction import transactional


class PublishingChannelService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PublishingChannelRepository(session)
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _sanitize_name(self, name: str) -> str:
        return sanitize_text(name).strip()[:256]

    def _normalize_config(
        self,
        config: dict[str, Any] | None,
        *,
        channel_type: PublishingChannelType,
    ) -> dict[str, Any]:
        if channel_type == PublishingChannelType.WEBHOOK:
            validated = validate_webhook_channel_config(config)
            return webhook_channel_config_to_dict(validated)
        if channel_type == PublishingChannelType.TELEGRAM:
            validated = validate_telegram_channel_config(config)
            return telegram_channel_config_to_dict(validated)
        if not config:
            return {}
        return dict(config)

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: PublishingChannelCreateRequest,
    ) -> PublishingChannelTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        try:
            channel_config = self._normalize_config(body.config, channel_type=body.type)
        except InvalidStateError:
            raise
        row = PublishingChannelTable(
            owner_id=owner_id,
            project_id=project_id,
            name=self._sanitize_name(body.name),
            channel_type=body.type,
            status=PublishingChannelStatus.ACTIVE,
            channel_config=channel_config,
            config_preview=build_config_preview(channel_config, channel_type=body.type),
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
    ) -> PublishingChannelTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.get_for_owner(
            channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )

    async def list(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        channel_type: PublishingChannelType | None = None,
        status: PublishingChannelStatus | None = None,
        limit: int = 100,
    ) -> list[PublishingChannelTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_for_project(
            project_id,
            owner_id=owner_id,
            include_archived=include_archived,
            channel_type=channel_type,
            status=status,
            limit=limit,
        )

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
        body: PublishingChannelUpdateRequest,
    ) -> PublishingChannelTable | None:
        row = await self.get(owner_id, project_id, channel_id)
        if row is None:
            return None

        if body.name is not None:
            row.name = self._sanitize_name(body.name)
        if body.status is not None:
            row.status = body.status
        if body.config is not None:
            row.channel_config = self._normalize_config(
                body.config,
                channel_type=row.channel_type,
            )
            row.config_preview = build_config_preview(
                row.channel_config,
                channel_type=row.channel_type,
            )
        row.updated_at = datetime.now(UTC)

        async with transactional(self._session):
            return await self._repo.update(row)

    async def delete(
        self,
        owner_id: UUID,
        project_id: UUID,
        channel_id: UUID,
    ) -> bool:
        row = await self.get(owner_id, project_id, channel_id)
        if row is None:
            return False
        row.status = PublishingChannelStatus.ARCHIVED
        row.updated_at = datetime.now(UTC)
        async with transactional(self._session):
            await self._repo.update(row)
        return True

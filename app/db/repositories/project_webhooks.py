"""Project webhook repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.project_webhook import ProjectWebhookTable
from app.db.repositories.base import BaseRepository


class ProjectWebhookRepository(BaseRepository[ProjectWebhookTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectWebhookTable)

    async def list_active_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        event_type: str | None = None,
    ) -> list[ProjectWebhookTable]:
        statement = select(ProjectWebhookTable).where(
            ProjectWebhookTable.project_id == project_id,
            ProjectWebhookTable.owner_id == owner_id,
            ProjectWebhookTable.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        if event_type is None:
            return rows
        return [
            row
            for row in rows
            if not row.subscribed_event_types or event_type in row.subscribed_event_types
        ]

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
    ) -> list[ProjectWebhookTable]:
        statement = (
            select(ProjectWebhookTable)
            .where(
                ProjectWebhookTable.project_id == project_id,
                ProjectWebhookTable.owner_id == owner_id,
            )
            .order_by(ProjectWebhookTable.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_for_owner(
        self,
        webhook_id: UUID,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> ProjectWebhookTable | None:
        statement = select(ProjectWebhookTable).where(
            ProjectWebhookTable.id == webhook_id,
            ProjectWebhookTable.owner_id == owner_id,
            ProjectWebhookTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

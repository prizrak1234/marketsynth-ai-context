"""Project outbound webhook subscription service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_webhook import ProjectWebhookTable
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.project_webhooks import ProjectWebhookRepository
from app.schemas.contracts import EventType
from app.schemas.crud import ProjectWebhookCreateRequest
from app.security.webhooks import generate_webhook_signing_secret
from app.services.transaction import transactional


class ProjectWebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProjectWebhookRepository(session)
        self._projects = ProjectRepository(session)

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: ProjectWebhookCreateRequest,
    ) -> tuple[ProjectWebhookTable, str] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None

        event_types = body.subscribed_event_types or [
            EventType.GRAPH_HANDOFF_PARENT_SYNCED.value,
        ]
        signing_secret = generate_webhook_signing_secret()
        row = ProjectWebhookTable(
            owner_id=owner_id,
            project_id=project_id,
            url=body.url.strip(),
            signing_secret=signing_secret,
            subscribed_event_types=event_types,
            is_active=True,
        )
        async with transactional(self._session):
            created = await self._repo.create(row)
        return created, signing_secret

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ProjectWebhookTable] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return await self._repo.list_for_project(project_id, owner_id=owner_id)

    async def list_active_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        event_type: str,
    ) -> list[ProjectWebhookTable]:
        return await self._repo.list_active_for_project(
            project_id,
            owner_id=owner_id,
            event_type=event_type,
        )

    async def deactivate(
        self,
        owner_id: UUID,
        project_id: UUID,
        webhook_id: UUID,
    ) -> ProjectWebhookTable | None:
        row = await self._repo.get_for_owner(
            webhook_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if row is None:
            return None
        row.is_active = False
        async with transactional(self._session):
            return await self._repo.update(row)

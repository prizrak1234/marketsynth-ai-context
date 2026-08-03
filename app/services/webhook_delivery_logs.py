"""Webhook delivery log service."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.webhook_delivery_logs import WebhookDeliveryLogRepository
from app.events.delivery_url import build_target_url_preview
from app.events.webhook_delivery import WebhookDeliveryResult
from app.schemas.contracts import WebhookDeliveryLogStatus
from app.services.transaction import transactional


class WebhookDeliveryLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WebhookDeliveryLogRepository(session)
        self._projects = ProjectRepository(session)

    async def record_attempt(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        event_outbox_id: UUID,
        event_type: str,
        attempt_number: int,
        target_url: str,
        webhook_id: UUID | None,
        result: WebhookDeliveryResult | None = None,
        status: WebhookDeliveryLogStatus | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WebhookDeliveryLogTable:
        if result is not None:
            log_status = WebhookDeliveryLogStatus(result.status)
            error_code = result.error_code
            error_message = result.error_message
            http_status = result.http_status_code
            duration_ms = result.duration_ms
            response_preview = result.response_preview
        else:
            log_status = status or WebhookDeliveryLogStatus.SKIPPED
            http_status = None
            duration_ms = None
            response_preview = None

        row = WebhookDeliveryLogTable(
            owner_id=owner_id,
            project_id=project_id,
            webhook_id=webhook_id,
            event_outbox_id=event_outbox_id,
            event_type=event_type,
            target_url_preview=build_target_url_preview(target_url),
            status=log_status,
            http_status_code=http_status,
            attempt_number=attempt_number,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
            response_preview=response_preview,
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        webhook_id: UUID | None = None,
        event_type: str | None = None,
        status: WebhookDeliveryLogStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookDeliveryLogTable] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return await self._repo.list_for_project(
            project_id,
            owner_id=owner_id,
            webhook_id=webhook_id,
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def cleanup_old_logs(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        older_than_days: int,
    ) -> int | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        created_before = utc_now() - timedelta(days=older_than_days)
        async with transactional(self._session):
            return await self._repo.delete_older_than(
                project_id,
                owner_id=owner_id,
                created_before=created_before,
            )

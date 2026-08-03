"""Drain pending event_outbox rows to project webhooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.event_outbox import EventOutboxTable
from app.events.outbox import EventOutboxService
from app.events.webhook_delivery import deliver_event_to_webhook, sanitize_delivery_error
from app.schemas.contracts import EventOutboxStatus, WebhookDeliveryLogStatus
from app.services.project_webhooks import ProjectWebhookService
from app.services.webhook_delivery_logs import WebhookDeliveryLogService


@dataclass(frozen=True)
class EventDispatchItemResult:
    event_id: UUID
    delivered: bool
    skipped: bool
    skip_reason: str | None
    webhook_count: int
    error: str | None


@dataclass(frozen=True)
class EventDispatchBatchResult:
    requested_limit: int
    dispatched_count: int
    skipped_count: int
    failed_count: int
    results: list[EventDispatchItemResult]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "requested_limit": self.requested_limit,
            "dispatched_count": self.dispatched_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "results": [
                {
                    "event_id": str(item.event_id),
                    "delivered": item.delivered,
                    "skipped": item.skipped,
                    "skip_reason": item.skip_reason,
                    "webhook_count": item.webhook_count,
                    "error": item.error,
                }
                for item in self.results
            ],
        }


class EventOutboxDispatcher:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = EventOutboxService(session)
        self._webhooks = ProjectWebhookService(session)
        self._delivery_logs = WebhookDeliveryLogService(session)

    async def _log_no_webhooks(self, event: EventOutboxTable) -> None:
        attempt_number = event.attempts + 1
        await self._delivery_logs.record_attempt(
            owner_id=event.owner_id,
            project_id=event.project_id,
            event_outbox_id=event.id,
            event_type=event.event_type.value,
            attempt_number=attempt_number,
            target_url="https://no-webhook.local/none",
            webhook_id=None,
            status=WebhookDeliveryLogStatus.SKIPPED,
            error_code="no_active_webhooks",
            error_message="no_active_webhooks",
        )

    async def dispatch_event(
        self,
        event: EventOutboxTable,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> EventDispatchItemResult:
        settings = get_settings()
        if event.status != EventOutboxStatus.PENDING:
            return EventDispatchItemResult(
                event_id=event.id,
                delivered=False,
                skipped=True,
                skip_reason=f"event_status_{event.status.value}",
                webhook_count=0,
                error=event.last_error,
            )

        hooks = await self._webhooks.list_active_for_project(
            event.owner_id,
            event.project_id,
            event_type=event.event_type.value,
        )
        if not hooks:
            await self._log_no_webhooks(event)
            return EventDispatchItemResult(
                event_id=event.id,
                delivered=False,
                skipped=True,
                skip_reason="no_active_webhooks",
                webhook_count=0,
                error=None,
            )

        attempt_number = event.attempts + 1
        success_count = 0
        errors: list[str] = []

        owns_client = http_client is None
        client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.event_outbox_webhook_timeout_seconds),
            trust_env=False,
        )
        try:
            for hook in hooks:
                result = await deliver_event_to_webhook(event, hook, client=client)
                await self._delivery_logs.record_attempt(
                    owner_id=event.owner_id,
                    project_id=event.project_id,
                    event_outbox_id=event.id,
                    event_type=event.event_type.value,
                    attempt_number=attempt_number,
                    target_url=hook.url,
                    webhook_id=hook.id,
                    result=result,
                )
                if result.status == "succeeded":
                    success_count += 1
                elif result.error_message:
                    errors.append(result.error_message)
        finally:
            if owns_client:
                await client.aclose()

        if success_count > 0:
            updated = await self._outbox.mark_sent(event)
            return EventDispatchItemResult(
                event_id=updated.id,
                delivered=True,
                skipped=False,
                skip_reason=None,
                webhook_count=len(hooks),
                error=None,
            )

        err_text = "; ".join(errors) if errors else "all_webhooks_failed"
        combined_error = sanitize_delivery_error(err_text)
        updated = await self._outbox.record_delivery_failure(
            event,
            error=combined_error,
            max_attempts=settings.event_outbox_dispatch_max_attempts,
        )
        is_dead = updated.status == EventOutboxStatus.DEAD_LETTERED
        return EventDispatchItemResult(
            event_id=updated.id,
            delivered=False,
            skipped=False,
            skip_reason="dead_lettered" if is_dead else None,
            webhook_count=len(hooks),
            error=updated.last_error,
        )

    async def dispatch_batch(
        self,
        *,
        limit: int | None = None,
        project_id: UUID | None = None,
        owner_id: UUID | None = None,
    ) -> EventDispatchBatchResult:
        settings = get_settings()
        batch_limit = limit if limit is not None else settings.event_outbox_dispatch_batch_limit
        pending = await self._outbox.list_pending(limit=batch_limit, project_id=project_id)
        if owner_id is not None:
            pending = [row for row in pending if row.owner_id == owner_id]

        results: list[EventDispatchItemResult] = []
        dispatched_count = 0
        skipped_count = 0
        failed_count = 0

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.event_outbox_webhook_timeout_seconds),
            trust_env=False,
        ) as client:
            for event in pending:
                item = await self.dispatch_event(event, http_client=client)
                results.append(item)
                if item.skipped:
                    skipped_count += 1
                elif item.delivered:
                    dispatched_count += 1
                else:
                    failed_count += 1

        return EventDispatchBatchResult(
            requested_limit=batch_limit,
            dispatched_count=dispatched_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            results=results,
        )

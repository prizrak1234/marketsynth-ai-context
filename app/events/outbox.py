"""Persist internal domain events to the DB outbox."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.event_outbox import EventOutboxTable
from app.db.repositories.event_outbox import EventOutboxRepository
from app.events.contracts import build_handoff_parent_synced_payload
from app.schemas.contracts import EventOutboxStatus, EventType
from app.schemas.operational_batch import EventOutboxReplayBatchResponse
from app.services.transaction import transactional

log = get_logger(__name__)


class EventOutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EventOutboxRepository(session)

    async def append_event(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        event_type: EventType,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
    ) -> EventOutboxTable | None:
        row = EventOutboxTable(
            owner_id=owner_id,
            project_id=project_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=EventOutboxStatus.PENDING,
            attempts=0,
        )
        try:
            async with transactional(self._session):
                return await self._repo.create(row)
        except Exception:
            log.warning(
                "event_outbox_append_failed",
                event_type=event_type.value,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                exc_info=True,
            )
            return None

    async def append_content_asset_approved(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        brief_id: UUID | None,
        asset_type: str,
        title: str,
        approved_at: str,
    ) -> EventOutboxTable | None:
        payload: dict[str, Any] = {
            "asset_id": str(asset_id),
            "brief_id": str(brief_id) if brief_id is not None else None,
            "type": asset_type,
            "title": title,
            "approved_at": approved_at,
        }
        return await self.append_event(
            owner_id=owner_id,
            project_id=project_id,
            event_type=EventType.CONTENT_ASSET_APPROVED,
            aggregate_type="content_asset",
            aggregate_id=asset_id,
            payload=payload,
        )

    async def append_content_asset_rollback_revision_created(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        source_asset_id: UUID,
        source_version_number: int,
        revision_asset_id: UUID,
        revision_number: int,
        created_at: str,
    ) -> EventOutboxTable | None:
        payload: dict[str, Any] = {
            "source_asset_id": str(source_asset_id),
            "source_version_number": source_version_number,
            "revision_asset_id": str(revision_asset_id),
            "revision_number": revision_number,
            "created_at": created_at,
        }
        return await self.append_event(
            owner_id=owner_id,
            project_id=project_id,
            event_type=EventType.CONTENT_ASSET_ROLLBACK_REVISION_CREATED,
            aggregate_type="content_asset",
            aggregate_id=revision_asset_id,
            payload=payload,
        )

    async def append_content_asset_archived(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        asset_id: UUID,
        brief_id: UUID | None,
        asset_type: str,
        title: str,
        archived_at: str,
    ) -> EventOutboxTable | None:
        payload: dict[str, Any] = {
            "asset_id": str(asset_id),
            "brief_id": str(brief_id) if brief_id is not None else None,
            "type": asset_type,
            "title": title,
            "archived_at": archived_at,
        }
        return await self.append_event(
            owner_id=owner_id,
            project_id=project_id,
            event_type=EventType.CONTENT_ASSET_ARCHIVED,
            aggregate_type="content_asset",
            aggregate_id=asset_id,
            payload=payload,
        )

    async def append_handoff_parent_synced(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        parent_run_id: UUID,
        child_run_id: UUID,
        child_run_status: str,
        child_run_executed: bool,
        dead_lettered: bool,
        synced_at: str,
    ) -> EventOutboxTable | None:
        payload = build_handoff_parent_synced_payload(
            parent_run_id=str(parent_run_id),
            child_run_id=str(child_run_id),
            child_run_status=child_run_status,
            child_run_executed=child_run_executed,
            dead_lettered=dead_lettered,
            synced_at=synced_at,
        )
        return await self.append_event(
            owner_id=owner_id,
            project_id=project_id,
            event_type=EventType.GRAPH_HANDOFF_PARENT_SYNCED,
            aggregate_type="agent_run",
            aggregate_id=parent_run_id,
            payload=payload,
        )

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        event_type: EventType | None = None,
        status: EventOutboxStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventOutboxTable]:
        return await self._repo.list_by_project(
            project_id,
            owner_id=owner_id,
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def list_pending(
        self,
        *,
        limit: int = 50,
        project_id: UUID | None = None,
    ) -> list[EventOutboxTable]:
        return await self._repo.list_pending(limit=limit, project_id=project_id)

    async def mark_sent(self, row: EventOutboxTable) -> EventOutboxTable:
        async with transactional(self._session):
            return await self._repo.mark_sent(row)

    async def get_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        event_id: UUID,
    ) -> EventOutboxTable | None:
        return await self._repo.get_for_project(
            event_id,
            owner_id=owner_id,
            project_id=project_id,
        )

    async def replay_batch(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        statuses: list[EventOutboxStatus],
        event_type: EventType | None,
        limit: int,
    ) -> EventOutboxReplayBatchResponse:
        rows = await self._repo.list_for_batch_replay(
            project_id,
            owner_id=owner_id,
            statuses=statuses,
            event_type=event_type,
            limit=limit,
        )
        matched_count = len(rows)
        replayed_count = 0
        skipped_count = 0
        for row in rows:
            if row.status == EventOutboxStatus.SENT:
                skipped_count += 1
                continue
            if row.status not in (
                EventOutboxStatus.PENDING,
                EventOutboxStatus.FAILED,
                EventOutboxStatus.DEAD_LETTERED,
            ):
                skipped_count += 1
                continue
            async with transactional(self._session):
                await self._repo.reset_for_replay(row)
            replayed_count += 1
        return EventOutboxReplayBatchResponse(
            matched_count=matched_count,
            replayed_count=replayed_count,
            skipped_count=skipped_count,
        )

    async def replay_event(
        self,
        owner_id: UUID,
        project_id: UUID,
        event_id: UUID,
    ) -> EventOutboxTable | None:
        row = await self.get_for_project(owner_id, project_id, event_id)
        if row is None:
            return None
        if row.status not in (
            EventOutboxStatus.PENDING,
            EventOutboxStatus.FAILED,
            EventOutboxStatus.DEAD_LETTERED,
        ):
            return None
        async with transactional(self._session):
            return await self._repo.reset_for_replay(row)

    async def record_delivery_failure(
        self,
        row: EventOutboxTable,
        *,
        error: str,
        max_attempts: int,
    ) -> EventOutboxTable:
        async with transactional(self._session):
            return await self._repo.record_delivery_failure(
                row,
                error=error,
                max_attempts=max_attempts,
            )

"""Batch replay and cleanup API contracts (Phase 3.12)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.contracts import EventOutboxStatus, EventType

REPLAYABLE_OUTBOX_STATUSES = frozenset(
    {
        EventOutboxStatus.PENDING,
        EventOutboxStatus.FAILED,
        EventOutboxStatus.DEAD_LETTERED,
    },
)


class EventOutboxReplayBatchRequest(BaseModel):
    statuses: list[EventOutboxStatus] = Field(
        default_factory=lambda: [
            EventOutboxStatus.FAILED,
            EventOutboxStatus.DEAD_LETTERED,
        ],
        min_length=1,
    )
    event_type: EventType | None = EventType.GRAPH_HANDOFF_PARENT_SYNCED
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("statuses")
    @classmethod
    def validate_replayable_statuses(
        cls,
        statuses: list[EventOutboxStatus],
    ) -> list[EventOutboxStatus]:
        invalid = [s for s in statuses if s not in REPLAYABLE_OUTBOX_STATUSES]
        if invalid:
            msg = "statuses must be pending, failed, or dead_lettered only"
            raise ValueError(msg)
        return statuses


class EventOutboxReplayBatchResponse(BaseModel):
    matched_count: int
    replayed_count: int
    skipped_count: int


class HandoffReplayBatchRequest(BaseModel):
    project_id: UUID
    limit: int = Field(default=50, ge=1, le=100)


class HandoffReplayBatchResponse(BaseModel):
    matched_count: int
    requeued_count: int
    skipped_count: int


class WebhookDeliveryCleanupResponse(BaseModel):
    deleted_count: int
    older_than_days: int

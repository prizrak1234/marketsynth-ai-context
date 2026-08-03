"""Publication job scheduling policy (Phase AI.76)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import InvalidStateError
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)

_TERMINAL_JOB_STATUSES = frozenset(
    {
        PublicationPackageJobStatus.DRY_RUN_SUCCEEDED,
        PublicationPackageJobStatus.SUCCEEDED,
        PublicationPackageJobStatus.FAILED,
        PublicationPackageJobStatus.CANCELLED,
    },
)


def normalize_scheduled_for(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise InvalidStateError("scheduled_for must be a timezone-aware UTC datetime")
    normalized = value.astimezone(UTC)
    if normalized <= datetime.now(UTC):
        raise InvalidStateError("scheduled_for must be in the future")
    return normalized


def assert_job_can_be_scheduled(job: object) -> None:
    status = getattr(job, "status", None)
    if status != PublicationPackageJobStatus.QUEUED:
        raise InvalidStateError("Only queued publication jobs can be scheduled")
    if status in _TERMINAL_JOB_STATUSES:
        raise InvalidStateError("Terminal publication jobs cannot be scheduled")

    schedule_status = getattr(job, "schedule_status", None)
    if schedule_status == PublicationPackageJobScheduleStatus.DISPATCHED:
        raise InvalidStateError("Dispatched jobs cannot be rescheduled")
    if schedule_status == PublicationPackageJobScheduleStatus.CANCELLED:
        pass  # allow scheduling after unschedule cancelled -> we set unscheduled on unschedule


def assert_job_can_be_unscheduled(job: object) -> None:
    schedule_status = getattr(job, "schedule_status", None)
    if schedule_status not in (
        PublicationPackageJobScheduleStatus.SCHEDULED,
        PublicationPackageJobScheduleStatus.DUE,
    ):
        raise InvalidStateError("Only scheduled or due jobs can be unscheduled")


def assert_job_ready_for_dispatch(job: object, *, now: datetime | None = None) -> None:
    anchor = now or datetime.now(UTC)
    status = getattr(job, "status", None)
    if status != PublicationPackageJobStatus.QUEUED:
        raise InvalidStateError("Only queued jobs can be dispatched from the scheduler")

    schedule_status = getattr(job, "schedule_status", None)
    if schedule_status not in (
        PublicationPackageJobScheduleStatus.SCHEDULED,
        PublicationPackageJobScheduleStatus.DUE,
    ):
        raise InvalidStateError("Job is not in a schedulable dispatch state")

    scheduled_for = getattr(job, "scheduled_for", None)
    if scheduled_for is None:
        raise InvalidStateError("Job has no scheduled_for timestamp")
    if scheduled_for.astimezone(UTC) > anchor:
        raise InvalidStateError("Job is not yet due for dispatch")

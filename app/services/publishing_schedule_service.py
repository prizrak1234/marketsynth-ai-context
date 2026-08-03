"""Publishing schedule service — explicit due scan and dispatch (Phase AI.77)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.base import ensure_naive_utc
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.repositories.publication_package_jobs import PublicationPackageJobRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.marketing.contracts import PublicationPackageStatus
from app.publishing.contracts import PublishingChannelStatus
from app.publishing.providers.registry import resolve_provider_type_for_channel
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublishingAuditEventType,
    PublishingDispatchMode,
)
from app.publishing_foundation.schedule_policy import (
    assert_job_can_be_scheduled,
    assert_job_can_be_unscheduled,
    assert_job_ready_for_dispatch,
    normalize_scheduled_for,
)
from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata
from app.services.projects_service import ProjectService
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publishing_audit_service import PublishingAuditService
from app.services.transaction import transactional

_FOUNDATION_CHANNEL_TYPES = frozenset({"telegram", "instagram", "linkedin", "blog"})


class PublishingScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = PublicationPackageJobRepository(session)
        self._packages = PublicationPackageRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._projects = ProjectService(session)
        self._job_service = PublicationPackageJobService(session)
        self._audit = PublishingAuditService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def schedule_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
        *,
        scheduled_for: datetime,
    ) -> PublicationPackageJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
        if row is None:
            return None

        assert_job_can_be_scheduled(row)
        when = ensure_naive_utc(normalize_scheduled_for(scheduled_for))
        row.scheduled_for = when
        row.schedule_status = PublicationPackageJobScheduleStatus.SCHEDULED
        row.last_dispatch_error = None

        async with transactional(self._session):
            updated = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_SCHEDULED,
                status="ok",
                channel_id=updated.channel_id,
                publication_package_job_id=updated.id,
                safe_metadata={
                    "job_id": str(updated.id),
                    "scheduled_for": when.isoformat(),
                },
            )
            return updated

    async def unschedule_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationPackageJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
        if row is None:
            return None

        assert_job_can_be_unscheduled(row)
        row.scheduled_for = None
        row.schedule_status = PublicationPackageJobScheduleStatus.UNSCHEDULED

        async with transactional(self._session):
            updated = await self._jobs.update(row)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=PublishingAuditEventType.JOB_UNSCHEDULED,
                status="ok",
                channel_id=updated.channel_id,
                publication_package_job_id=updated.id,
                safe_metadata={"job_id": str(updated.id)},
            )
            return updated

    async def list_due_jobs(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[PublicationPackageJobTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._jobs.list_due_for_project(
            owner_id,
            project_id,
            now=now,
            limit=limit,
        )

    async def mark_due(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
        *,
        now: datetime | None = None,
    ) -> PublicationPackageJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
        if row is None:
            return None

        anchor = now or datetime.now(UTC)
        assert_job_ready_for_dispatch(row, now=anchor)
        if row.schedule_status == PublicationPackageJobScheduleStatus.SCHEDULED:
            row.schedule_status = PublicationPackageJobScheduleStatus.DUE
            async with transactional(self._session):
                updated = await self._jobs.update(row)
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_MARKED_DUE,
                    status="ok",
                    channel_id=updated.channel_id,
                    publication_package_job_id=updated.id,
                    safe_metadata={"job_id": str(updated.id)},
                )
                return updated
        return row

    async def _assert_dispatch_preconditions(
        self,
        row: PublicationPackageJobTable,
        channel: object,
    ) -> None:
        package = await self._packages.get_by_id_for_owner(
            row.publication_package_id,
            row.owner_id,
            row.project_id,
        )
        if package is None or package.status != PublicationPackageStatus.APPROVED:
            raise InvalidStateError(
                "Publication package must remain approved for scheduled dispatch",
            )

        channel_type = getattr(getattr(channel, "channel_type", None), "value", None)
        if channel_type not in _FOUNDATION_CHANNEL_TYPES:
            raise InvalidStateError("Unsupported publishing channel")
        if getattr(channel, "status", None) != PublishingChannelStatus.ACTIVE:
            raise InvalidStateError("Publishing channel must be active for dispatch")

    async def dispatch_due_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
        *,
        mode: PublishingDispatchMode,
        now: datetime | None = None,
    ) -> PublicationPackageJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        row = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
        if row is None:
            return None

        anchor = now or datetime.now(UTC)
        if row.schedule_status == PublicationPackageJobScheduleStatus.SCHEDULED:
            row = await self.mark_due(owner_id, project_id, job_id, now=anchor)
            if row is None:
                return None

        assert_job_ready_for_dispatch(row, now=anchor)

        channel = await self._channels.get_for_owner(
            row.channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if channel is None:
            return None

        await self._assert_dispatch_preconditions(row, channel)

        if mode == PublishingDispatchMode.REAL:
            try:
                resolve_provider_type_for_channel(channel.channel_type.value)
            except InvalidStateError as exc:
                raise InvalidStateError(
                    "Real publishing is not enabled for this channel",
                ) from exc

        row.dispatch_attempts += 1
        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=PublishingAuditEventType.JOB_DISPATCH_REQUESTED,
            status="ok",
            channel_id=row.channel_id,
            publication_package_job_id=row.id,
            safe_metadata={
                "job_id": str(row.id),
                "channel_type": channel.channel_type.value,
                "provider": mode.value,
                "dispatch_mode": mode.value,
            },
        )

        try:
            if mode == PublishingDispatchMode.DRY_RUN:
                result = await self._job_service.execute_dry_run(
                    owner_id,
                    project_id,
                    job_id,
                )
            else:
                result = await self._job_service.execute_job(
                    owner_id,
                    project_id,
                    job_id,
                )
        except InvalidStateError:
            row = await self._jobs.get_by_id_for_owner(job_id, owner_id, project_id)
            if row is not None:
                row.last_dispatch_error = sanitize_publishing_metadata(
                    {"error_code": "dispatch_rejected"},
                )
                await self._jobs.update(row)
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_DISPATCH_FAILED,
                    status="failed",
                    channel_id=row.channel_id,
                    publication_package_job_id=row.id,
                    safe_metadata={
                        "job_id": str(row.id),
                        "channel_type": channel.channel_type.value,
                        "provider": mode.value,
                    },
                )
            raise

        if result is None:
            return None

        result.schedule_status = PublicationPackageJobScheduleStatus.DISPATCHED
        async with transactional(self._session):
            updated = await self._jobs.update(result)
            if updated.error:
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_DISPATCH_FAILED,
                    status="failed",
                    channel_id=updated.channel_id,
                    publication_package_job_id=updated.id,
                    safe_metadata={
                        "job_id": str(updated.id),
                        "channel_type": channel.channel_type.value,
                        "provider": mode.value,
                        "error_code": (updated.error or {}).get("error_code"),
                    },
                )
                updated.last_dispatch_error = sanitize_publishing_metadata(updated.error)
                updated = await self._jobs.update(updated)
            else:
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=PublishingAuditEventType.JOB_DISPATCHED,
                    status="ok",
                    channel_id=updated.channel_id,
                    publication_package_job_id=updated.id,
                    safe_metadata={
                        "job_id": str(updated.id),
                        "channel_type": channel.channel_type.value,
                        "provider": mode.value,
                        "status": updated.status.value,
                    },
                )
            return updated

"""Publishing foundation metrics — package jobs + real publish stats (Phase AI.64/74)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublishingChannelTable
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
    PublishingFoundationMetrics,
)


class PublishingFoundationMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project_metrics(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublishingFoundationMetrics:
        status_rows = await self._session.execute(
            select(PublicationPackageJobTable.status, func.count())
            .where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
            )
            .group_by(PublicationPackageJobTable.status),
        )
        jobs_by_status = {row[0].value: int(row[1]) for row in status_rows.all()}
        for status in PublicationPackageJobStatus:
            jobs_by_status.setdefault(status.value, 0)

        channel_rows = await self._session.execute(
            select(PublishingChannelTable.channel_type, func.count())
            .join(
                PublicationPackageJobTable,
                PublicationPackageJobTable.channel_id == PublishingChannelTable.id,
            )
            .where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
            )
            .group_by(PublishingChannelTable.channel_type),
        )
        jobs_by_channel_type = {row[0].value: int(row[1]) for row in channel_rows.all()}

        latest = await self._session.execute(
            select(func.max(PublicationPackageJobTable.finished_at)).where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
                PublicationPackageJobTable.finished_at.is_not(None),
            ),
        )
        latest_activity_at: datetime | None = latest.scalar_one_or_none()

        real_jobs_succeeded = jobs_by_status.get(
            PublicationPackageJobStatus.SUCCEEDED.value,
            0,
        )

        meta_rows = await self._session.execute(
            select(
                PublicationPackageJobTable.result_metadata,
                PublicationPackageJobTable.error,
                PublicationPackageJobTable.status,
            ).where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
            ),
        )
        jobs_by_provider: dict[str, int] = {}
        real_jobs_failed = 0
        for result_metadata, error, job_status in meta_rows.all():
            provider = None
            if isinstance(result_metadata, dict):
                provider = result_metadata.get("provider")
            if provider is None and isinstance(error, dict):
                provider = error.get("provider")
            if provider:
                jobs_by_provider[provider] = jobs_by_provider.get(provider, 0) + 1
            if (
                job_status == PublicationPackageJobStatus.FAILED
                and isinstance(error, dict)
                and error.get("provider") == "telegram"
            ):
                real_jobs_failed += 1

        anchor = datetime.now(UTC)
        scheduled_jobs_total = int(
            (
                await self._session.execute(
                    select(func.count()).where(
                        PublicationPackageJobTable.owner_id == owner_id,
                        PublicationPackageJobTable.project_id == project_id,
                        PublicationPackageJobTable.schedule_status.in_(
                            (
                                PublicationPackageJobScheduleStatus.SCHEDULED,
                                PublicationPackageJobScheduleStatus.DUE,
                            ),
                        ),
                    ),
                )
            ).scalar_one()
            or 0,
        )
        due_jobs_total = int(
            (
                await self._session.execute(
                    select(func.count()).where(
                        PublicationPackageJobTable.owner_id == owner_id,
                        PublicationPackageJobTable.project_id == project_id,
                        PublicationPackageJobTable.status
                        == PublicationPackageJobStatus.QUEUED,
                        PublicationPackageJobTable.schedule_status.in_(
                            (
                                PublicationPackageJobScheduleStatus.SCHEDULED,
                                PublicationPackageJobScheduleStatus.DUE,
                            ),
                        ),
                        PublicationPackageJobTable.scheduled_for.is_not(None),
                        PublicationPackageJobTable.scheduled_for <= anchor,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        dispatched_jobs_total = int(
            (
                await self._session.execute(
                    select(func.count()).where(
                        PublicationPackageJobTable.owner_id == owner_id,
                        PublicationPackageJobTable.project_id == project_id,
                        PublicationPackageJobTable.schedule_status
                        == PublicationPackageJobScheduleStatus.DISPATCHED,
                    ),
                )
            ).scalar_one()
            or 0,
        )
        dispatch_failed_total = int(
            (
                await self._session.execute(
                    select(func.count()).where(
                        PublicationPackageJobTable.owner_id == owner_id,
                        PublicationPackageJobTable.project_id == project_id,
                        PublicationPackageJobTable.last_dispatch_error.is_not(None),
                    ),
                )
            ).scalar_one()
            or 0,
        )
        scheduled_channel_rows = await self._session.execute(
            select(PublishingChannelTable.channel_type, func.count())
            .join(
                PublicationPackageJobTable,
                PublicationPackageJobTable.channel_id == PublishingChannelTable.id,
            )
            .where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
                PublicationPackageJobTable.schedule_status.in_(
                    (
                        PublicationPackageJobScheduleStatus.SCHEDULED,
                        PublicationPackageJobScheduleStatus.DUE,
                    ),
                ),
            )
            .group_by(PublishingChannelTable.channel_type),
        )
        scheduled_jobs_by_channel_type = {
            row[0].value: int(row[1]) for row in scheduled_channel_rows.all()
        }

        return PublishingFoundationMetrics(
            jobs_total=sum(jobs_by_status.values()),
            jobs_by_status=jobs_by_status,
            jobs_by_channel_type=jobs_by_channel_type,
            latest_activity_at=latest_activity_at,
            real_jobs_total=real_jobs_succeeded + real_jobs_failed,
            real_jobs_succeeded=real_jobs_succeeded,
            real_jobs_failed=real_jobs_failed,
            jobs_by_provider=jobs_by_provider,
            scheduled_jobs_total=scheduled_jobs_total,
            due_jobs_total=due_jobs_total,
            dispatched_jobs_total=dispatched_jobs_total,
            dispatch_failed_total=dispatch_failed_total,
            scheduled_jobs_by_channel_type=scheduled_jobs_by_channel_type,
        )

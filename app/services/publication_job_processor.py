"""Process queued publication jobs via mock dispatcher (Phase 6.1)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.events.webhook_delivery import sanitize_delivery_error
from app.publishing.contracts import PublicationDeliveryLogStatus, PublishingChannelType
from app.publishing.dispatch_result import PublicationDispatchResult
from app.publishing.dispatcher import PublicationDispatcher
from app.services.publication_delivery_log_service import PublicationDeliveryLogService
from app.services.publication_scheduler_service import PublicationSchedulerService
from app.services.transaction import transactional

log = get_logger(__name__)


@dataclass(frozen=True)
class PublicationJobProcessBatchResult:
    processed_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    requeued_count: int = 0

    def to_api_dict(self) -> dict[str, int]:
        return {
            "processed_count": self.processed_count,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "requeued_count": self.requeued_count,
        }


class PublicationJobProcessor:
    def __init__(
        self,
        session: AsyncSession,
        *,
        dispatcher: PublicationDispatcher | None = None,
    ) -> None:
        self._session = session
        self._jobs = PublicationJobRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._versions = ContentAssetVersionRepository(session)
        self._delivery_logs = PublicationDeliveryLogService(session)
        self._dispatcher = dispatcher or PublicationDispatcher()

    async def process_batch(
        self,
        *,
        limit: int | None = None,
        project_id: UUID | None = None,
        owner_id: UUID | None = None,
    ) -> PublicationJobProcessBatchResult:
        settings = get_settings()
        batch_limit = limit if limit is not None else settings.event_outbox_dispatch_batch_limit
        # First, release due scheduled jobs into the queue.
        await PublicationSchedulerService(self._session).release_due_jobs()
        queued = await self._jobs.list_queued(
            limit=batch_limit,
            project_id=project_id,
            owner_id=owner_id,
        )

        result = PublicationJobProcessBatchResult()
        for job in queued:
            item = await self._process_one(
                job.id,
                max_attempts=settings.publication_job_max_attempts,
            )
            if item is None:
                continue
            result = PublicationJobProcessBatchResult(
                processed_count=result.processed_count + 1,
                succeeded_count=result.succeeded_count + item.succeeded_count,
                failed_count=result.failed_count + item.failed_count,
                skipped_count=result.skipped_count + item.skipped_count,
                requeued_count=result.requeued_count + item.requeued_count,
            )
        return result

    async def _process_one(
        self,
        job_id: UUID,
        *,
        max_attempts: int,
    ) -> PublicationJobProcessBatchResult | None:
        async with transactional(self._session):
            claimed = await self._jobs.claim_queued_job(job_id)
        if claimed is None:
            return None

        attempt_number = claimed.attempts + 1
        channel = await self._channels.get_for_owner(
            claimed.channel_id,
            owner_id=claimed.owner_id,
            project_id=claimed.project_id,
        )
        if channel is None:
            return await self._finalize_missing_resources(
                claimed,
                attempt_number=attempt_number,
                error="publishing_channel_not_found",
            )

        asset_version = await self._versions.get_version(
            claimed.asset_id,
            claimed.asset_version_number,
            claimed.owner_id,
            claimed.project_id,
        )
        if asset_version is None:
            return await self._finalize_missing_resources(
                claimed,
                attempt_number=attempt_number,
                error="approved_version_not_found",
            )

        settings = get_settings()
        try:
            dispatch_result = await asyncio.wait_for(
                self._dispatcher.dispatch(claimed, channel, asset_version),
                timeout=settings.publication_delivery_timeout_seconds,
            )
        except TimeoutError:
            dispatch_result = PublicationDispatchResult(
                status=PublicationDeliveryLogStatus.FAILED,
                duration_ms=settings.publication_delivery_timeout_seconds * 1000,
                error_code="timeout",
                error_message=sanitize_delivery_error("publication_delivery_timeout"),
            )
        except Exception:
            log.exception(
                "publication_dispatch_failed",
                publication_job_id=str(claimed.id),
                project_id=str(claimed.project_id),
            )
            dispatch_result = PublicationDispatchResult(
                status=PublicationDeliveryLogStatus.FAILED,
                duration_ms=0,
                error_code="dispatch_error",
                error_message=sanitize_delivery_error("publication_dispatch_failed"),
            )

        await self._delivery_logs.record_attempt(
            owner_id=claimed.owner_id,
            project_id=claimed.project_id,
            publication_job_id=claimed.id,
            channel_id=channel.id,
            channel_type=channel.channel_type,
            attempt_number=attempt_number,
            result=dispatch_result,
        )

        if dispatch_result.status == PublicationDeliveryLogStatus.SUCCEEDED:
            async with transactional(self._session):
                await self._jobs.mark_succeeded(claimed)
            return PublicationJobProcessBatchResult(
                processed_count=1,
                succeeded_count=1,
            )

        if dispatch_result.status == PublicationDeliveryLogStatus.SKIPPED:
            error = dispatch_result.error_message or "unsupported_channel_adapter"
            async with transactional(self._session):
                claimed.attempts = attempt_number
                await self._jobs.mark_failed(claimed, error=error)
            return PublicationJobProcessBatchResult(
                processed_count=1,
                failed_count=1,
                skipped_count=1,
            )

        error = dispatch_result.error_message or "publication_delivery_failed"
        if attempt_number >= max_attempts:
            async with transactional(self._session):
                claimed.attempts = attempt_number
                await self._jobs.mark_failed(claimed, error=error)
            return PublicationJobProcessBatchResult(processed_count=1, failed_count=1)

        async with transactional(self._session):
            await self._jobs.requeue_after_failure(claimed, error=error)
        return PublicationJobProcessBatchResult(processed_count=1, requeued_count=1)

    async def _finalize_missing_resources(
        self,
        job: object,
        *,
        attempt_number: int,
        error: str,
    ) -> PublicationJobProcessBatchResult:
        from app.db.models.publishing import PublicationJobTable

        assert isinstance(job, PublicationJobTable)
        safe_error = sanitize_delivery_error(error)
        dispatch_result = PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=0,
            error_code=error,
            error_message=safe_error,
        )
        channel_row = await self._channels.get_for_owner(
            job.channel_id,
            owner_id=job.owner_id,
            project_id=job.project_id,
        )
        if channel_row is not None:
            channel_type = channel_row.channel_type
        else:
            preview_type = str(job.payload_preview.get("channel_type", "custom"))
            try:
                channel_type = PublishingChannelType(preview_type)
            except ValueError:
                channel_type = PublishingChannelType.CUSTOM
        await self._delivery_logs.record_attempt(
            owner_id=job.owner_id,
            project_id=job.project_id,
            publication_job_id=job.id,
            channel_id=job.channel_id,
            channel_type=channel_type,
            attempt_number=attempt_number,
            result=dispatch_result,
        )
        async with transactional(self._session):
            job.attempts = attempt_number
            await self._jobs.mark_failed(job, error=safe_error)
        return PublicationJobProcessBatchResult(processed_count=1, failed_count=1)

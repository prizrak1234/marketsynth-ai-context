"""Publication dispatch — routes jobs to channel adapters (Phase 6.1+)."""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.db.models.marketing import ContentAssetVersionTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.events.webhook_delivery import sanitize_delivery_error
from app.publishing.adapters.telegram import dispatch_telegram_publication
from app.publishing.adapters.webhook import dispatch_webhook_publication
from app.publishing.contracts import PublicationDeliveryLogStatus, PublishingChannelType
from app.publishing.dispatch_result import PublicationDispatchResult, truncate_preview


class PublicationDispatcher:
    """Routes publication jobs to channel adapters."""

    async def dispatch(
        self,
        job: PublicationJobTable,
        channel: PublishingChannelTable,
        asset_version: ContentAssetVersionTable,
    ) -> PublicationDispatchResult:
        preview = dict(job.payload_preview or {})
        settings = get_settings()

        if channel.channel_type == PublishingChannelType.WEBHOOK:
            return await dispatch_webhook_publication(
                job,
                channel,
                asset_version,
                timeout_seconds=settings.publication_delivery_timeout_seconds,
            )

        if channel.channel_type == PublishingChannelType.TELEGRAM:
            raw_text = (asset_version.body or asset_version.title or "").strip()
            text = raw_text[:4000] if raw_text else ""
            metadata = dict(asset_version.version_metadata or {})
            media_url = metadata.get("media_url") or metadata.get("image_url")
            return await dispatch_telegram_publication(
                channel.channel_config,
                text=text,
                media_url=media_url,
            )

        if channel.channel_type == PublishingChannelType.CUSTOM:
            started = time.perf_counter()
            duration_ms = int((time.perf_counter() - started) * 1000)
            return PublicationDispatchResult(
                status=PublicationDeliveryLogStatus.SUCCEEDED,
                duration_ms=duration_ms,
                response_preview=truncate_preview(
                    "noop_dispatch "
                    f"channel={channel.name} "
                    f"asset_version={job.asset_version_number}",
                ),
            )

        started = time.perf_counter()
        duration_ms = int((time.perf_counter() - started) * 1000)
        channel_label = channel.channel_type.value
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.SKIPPED,
            duration_ms=duration_ms,
            error_code="unsupported_channel_adapter",
            error_message=sanitize_delivery_error(
                f"Channel adapter not enabled for type={channel_label}",
            ),
            response_preview=truncate_preview(str(preview.get("channel_type", channel_label))),
        )

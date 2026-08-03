"""Dry-run publishing provider — default, no HTTP (Phase AI.70)."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublishingChannelTable
from app.publishing.providers.base import PublishingProvider
from app.publishing.providers.contracts import (
    PublishingExecutionInput,
    PublishingExecutionResult,
    PublishingProviderType,
)
from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata

_REQUIRED_SNAPSHOT_KEYS = frozenset(
    {"publication_package_id", "channel", "title", "body"},
)


class DryRunPublishingProvider:
    async def publish(
        self,
        job: PublicationPackageJobTable,
        channel: PublishingChannelTable,
        payload_snapshot: dict[str, Any],
        *,
        execution_input: PublishingExecutionInput,
    ) -> PublishingExecutionResult:
        started = time.perf_counter()
        missing = _REQUIRED_SNAPSHOT_KEYS - set(payload_snapshot.keys())
        if missing:
            return PublishingExecutionResult(
                success=False,
                provider=PublishingProviderType.DRY_RUN,
                error_code="validation_error",
                error_message=(
                    f"payload_snapshot missing required fields: {', '.join(sorted(missing))}"
                ),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        digest = hashlib.sha256(
            json.dumps(payload_snapshot, sort_keys=True, default=str).encode(),
        ).hexdigest()[:16]
        metadata = sanitize_publishing_metadata(
            {
                "dry_run": True,
                "provider": "dry_run",
                "snapshot_digest": digest,
                "channel": str(payload_snapshot.get("channel", "")),
                "title_length": len(str(payload_snapshot.get("title", ""))),
                "body_length": len(str(payload_snapshot.get("body", ""))),
            },
        )
        return PublishingExecutionResult(
            success=True,
            provider=PublishingProviderType.DRY_RUN,
            result_metadata=metadata,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


def get_dry_run_provider() -> PublishingProvider:
    return DryRunPublishingProvider()

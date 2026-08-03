"""Deterministic dry-run publisher — no HTTP (Phase AI.63, legacy import path)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.publishing_foundation.base import PublishingProvider
from app.publishing_foundation.contracts import DryRunPublishResult
from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata

_REQUIRED_SNAPSHOT_KEYS = frozenset(
    {"publication_package_id", "channel", "title", "body"},
)


class DryRunPublishingProvider:
    def dry_run_publish(self, payload_snapshot: dict[str, Any]) -> DryRunPublishResult:
        missing = _REQUIRED_SNAPSHOT_KEYS - set(payload_snapshot.keys())
        if missing:
            raise ValueError(
                f"payload_snapshot missing required fields: {', '.join(sorted(missing))}",
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
        return DryRunPublishResult(result_metadata=metadata)


def get_dry_run_provider() -> PublishingProvider:
    return DryRunPublishingProvider()

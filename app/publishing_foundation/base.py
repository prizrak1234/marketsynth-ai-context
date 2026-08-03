"""Publishing provider interface — dry-run only (Phase AI.63)."""

from __future__ import annotations

from typing import Protocol

from app.publishing_foundation.contracts import DryRunPublishResult


class PublishingProvider(Protocol):
    def dry_run_publish(self, payload_snapshot: dict) -> DryRunPublishResult: ...

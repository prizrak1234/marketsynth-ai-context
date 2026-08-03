"""Publishing provider interface (Phase AI.70)."""

from __future__ import annotations

from typing import Protocol

from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublishingChannelTable
from app.publishing.providers.contracts import PublishingExecutionInput, PublishingExecutionResult


class PublishingProvider(Protocol):
    async def publish(
        self,
        job: PublicationPackageJobTable,
        channel: PublishingChannelTable,
        payload_snapshot: dict,
        *,
        execution_input: PublishingExecutionInput,
    ) -> PublishingExecutionResult: ...

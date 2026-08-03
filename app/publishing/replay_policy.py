"""Publication job replay policy — failed/cancelled only (Phase 6.3)."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.db.models.marketing import ContentAssetTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.marketing.contracts import ContentAssetStatus
from app.publishing.contracts import PublicationJobStatus, PublishingChannelStatus

REPLAYABLE_PUBLICATION_JOB_STATUSES = frozenset(
    {
        PublicationJobStatus.FAILED,
        PublicationJobStatus.CANCELLED,
    },
)


def assert_publication_job_replayable(job: PublicationJobTable) -> None:
    if job.status not in REPLAYABLE_PUBLICATION_JOB_STATUSES:
        raise InvalidStateError(
            f"Publication job cannot be replayed (status={job.status.value})",
        )


def assert_replay_prerequisites(
    job: PublicationJobTable,
    *,
    asset: ContentAssetTable | None,
    channel: PublishingChannelTable | None,
) -> None:
    if asset is None:
        raise InvalidStateError("Content asset for publication job not found")
    if channel is None:
        raise InvalidStateError("Publishing channel for publication job not found")
    if channel.status != PublishingChannelStatus.ACTIVE:
        raise InvalidStateError(
            f"Publishing channel is not active (status={channel.status.value})",
        )
    if asset.status != ContentAssetStatus.APPROVED:
        raise InvalidStateError(
            "Content asset must remain approved to replay publication job",
        )
    if asset.approved_version_number is None:
        raise InvalidStateError(
            "Content asset has no approved_version_number",
        )
    if asset.approved_version_number != job.asset_version_number:
        raise InvalidStateError(
            "Content asset approved version does not match publication job version",
        )

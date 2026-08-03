"""Publication job replay — reset to queued without auto-dispatch (Phase 6.3)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.publishing.replay_policy import (
    REPLAYABLE_PUBLICATION_JOB_STATUSES,
    assert_publication_job_replayable,
    assert_replay_prerequisites,
)
from app.schemas.publishing import (
    PublicationJobReplayBatchRequest,
    PublicationJobReplayBatchResponse,
)
from app.services.transaction import transactional


class PublicationReplayService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = PublicationJobRepository(session)
        self._assets = ContentAssetRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _replay_row(
        self,
        row: PublicationJobTable,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> bool:
        assert_publication_job_replayable(row)
        asset = await self._assets.get_for_project(
            row.asset_id,
            owner_id,
            project_id,
        )
        channel = await self._channels.get_for_owner(
            row.channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        assert_replay_prerequisites(row, asset=asset, channel=channel)
        async with transactional(self._session):
            await self._jobs.reset_for_replay(row)
        return True

    async def replay_job(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        row = await self._jobs.get_for_owner(job_id, owner_id=owner_id, project_id=project_id)
        if row is None:
            return None
        await self._replay_row(row, owner_id=owner_id, project_id=project_id)
        return await self._jobs.get_for_owner(job_id, owner_id=owner_id, project_id=project_id)

    async def replay_batch(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: PublicationJobReplayBatchRequest,
    ) -> PublicationJobReplayBatchResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        statuses = list(body.statuses)
        rows = await self._jobs.list_for_batch_replay(
            project_id,
            owner_id=owner_id,
            statuses=statuses,
            channel_id=body.channel_id,
            limit=body.limit,
        )
        matched_count = len(rows)
        replayed_count = 0
        skipped_count = 0

        for row in rows:
            if row.status not in REPLAYABLE_PUBLICATION_JOB_STATUSES:
                skipped_count += 1
                continue
            try:
                if await self._replay_row(row, owner_id=owner_id, project_id=project_id):
                    replayed_count += 1
            except Exception:  # noqa: BLE001 — skip rows that fail replay validation
                skipped_count += 1

        return PublicationJobReplayBatchResponse(
            matched_count=matched_count,
            replayed_count=replayed_count,
            skipped_count=skipped_count,
        )

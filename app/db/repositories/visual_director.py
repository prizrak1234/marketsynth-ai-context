"""Repositories for Visual Director entities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.visual_director import (
    ImageAssetTable,
    ImageAssetVersionTable,
    VisualInputSnapshotTable,
    VisualRequestTable,
    VisualRunCandidateTable,
    VisualRunTable,
)
from app.schemas.contracts import VisualRunStatus

_ACTIVE_RUN_STATUSES = frozenset(
    {
        VisualRunStatus.QUEUED,
        VisualRunStatus.RUNNING,
    }
)


class VisualRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: VisualRequestTable) -> VisualRequestTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: VisualRequestTable) -> VisualRequestTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRequestTable | None:
        result = await self._session.execute(
            select(VisualRequestTable).where(
                VisualRequestTable.id == request_id,
                VisualRequestTable.owner_id == owner_id,
                VisualRequestTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[VisualRequestTable]:
        result = await self._session.execute(
            select(VisualRequestTable)
            .where(
                VisualRequestTable.owner_id == owner_id,
                VisualRequestTable.project_id == project_id,
            )
            .order_by(VisualRequestTable.updated_at.desc())
        )
        return list(result.scalars().all())

    async def next_version(self, project_id: UUID) -> int:
        result = await self._session.execute(
            select(VisualRequestTable.version)
            .where(VisualRequestTable.project_id == project_id)
            .order_by(VisualRequestTable.version.desc())
            .limit(1)
        )
        current = result.scalar_one_or_none()
        return 1 if current is None else int(current) + 1

    async def latest_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRequestTable | None:
        result = await self._session.execute(
            select(VisualRequestTable)
            .where(
                VisualRequestTable.owner_id == owner_id,
                VisualRequestTable.project_id == project_id,
            )
            .order_by(VisualRequestTable.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class VisualInputSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: VisualInputSnapshotTable) -> VisualInputSnapshotTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row


class VisualRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: VisualRunTable) -> VisualRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: VisualRunTable) -> VisualRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRunTable | None:
        result = await self._session.execute(
            select(VisualRunTable).where(
                VisualRunTable.id == run_id,
                VisualRunTable.owner_id == owner_id,
                VisualRunTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_request(
        self,
        visual_request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRunTable | None:
        result = await self._session.execute(
            select(VisualRunTable)
            .where(
                VisualRunTable.visual_request_id == visual_request_id,
                VisualRunTable.owner_id == owner_id,
                VisualRunTable.project_id == project_id,
                VisualRunTable.status.in_(list(_ACTIVE_RUN_STATUSES)),
            )
            .order_by(VisualRunTable.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self,
        visual_request_id: UUID,
        idempotency_key: str,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRunTable | None:
        result = await self._session.execute(
            select(VisualRunTable)
            .where(
                VisualRunTable.visual_request_id == visual_request_id,
                VisualRunTable.idempotency_key == idempotency_key,
                VisualRunTable.owner_id == owner_id,
                VisualRunTable.project_id == project_id,
            )
            .order_by(VisualRunTable.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class VisualRunCandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: VisualRunCandidateTable) -> VisualRunCandidateTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: VisualRunCandidateTable) -> VisualRunCandidateTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_for_run(
        self,
        visual_run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[VisualRunCandidateTable]:
        result = await self._session.execute(
            select(VisualRunCandidateTable)
            .where(
                VisualRunCandidateTable.visual_run_id == visual_run_id,
                VisualRunCandidateTable.owner_id == owner_id,
                VisualRunCandidateTable.project_id == project_id,
            )
            .order_by(VisualRunCandidateTable.candidate_index.asc())
        )
        return list(result.scalars().all())

    async def list_for_request(
        self,
        visual_request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[VisualRunCandidateTable]:
        result = await self._session.execute(
            select(VisualRunCandidateTable)
            .where(
                VisualRunCandidateTable.visual_request_id == visual_request_id,
                VisualRunCandidateTable.owner_id == owner_id,
                VisualRunCandidateTable.project_id == project_id,
            )
            .order_by(
                VisualRunCandidateTable.created_at.desc(),
                VisualRunCandidateTable.candidate_index.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_asset(
        self,
        image_asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> VisualRunCandidateTable | None:
        result = await self._session.execute(
            select(VisualRunCandidateTable).where(
                VisualRunCandidateTable.image_asset_id == image_asset_id,
                VisualRunCandidateTable.owner_id == owner_id,
                VisualRunCandidateTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()


class ImageAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: ImageAssetTable) -> ImageAssetTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: ImageAssetTable) -> ImageAssetTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ImageAssetTable | None:
        result = await self._session.execute(
            select(ImageAssetTable).where(
                ImageAssetTable.id == asset_id,
                ImageAssetTable.owner_id == owner_id,
                ImageAssetTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_version(self, row: ImageAssetVersionTable) -> ImageAssetVersionTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_versions(
        self,
        image_asset_id: UUID,
    ) -> list[ImageAssetVersionTable]:
        result = await self._session.execute(
            select(ImageAssetVersionTable)
            .where(ImageAssetVersionTable.image_asset_id == image_asset_id)
            .order_by(ImageAssetVersionTable.version_number.asc())
        )
        return list(result.scalars().all())

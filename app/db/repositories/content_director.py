"""Repositories for Content Director entities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content_director import (
    ContentInputSnapshotTable,
    ContentRequestTable,
    ContentRunCandidateTable,
    ContentRunTable,
)
from app.schemas.contracts import ContentRunStatus

_ACTIVE_RUN_STATUSES = frozenset(
    {
        ContentRunStatus.QUEUED,
        ContentRunStatus.RUNNING,
    }
)


class ContentRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: ContentRequestTable) -> ContentRequestTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: ContentRequestTable) -> ContentRequestTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRequestTable | None:
        result = await self._session.execute(
            select(ContentRequestTable).where(
                ContentRequestTable.id == request_id,
                ContentRequestTable.owner_id == owner_id,
                ContentRequestTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ContentRequestTable]:
        result = await self._session.execute(
            select(ContentRequestTable)
            .where(
                ContentRequestTable.owner_id == owner_id,
                ContentRequestTable.project_id == project_id,
            )
            .order_by(ContentRequestTable.updated_at.desc())
        )
        return list(result.scalars().all())

    async def next_version(self, project_id: UUID) -> int:
        result = await self._session.execute(
            select(ContentRequestTable.version)
            .where(ContentRequestTable.project_id == project_id)
            .order_by(ContentRequestTable.version.desc())
            .limit(1)
        )
        current = result.scalar_one_or_none()
        return 1 if current is None else int(current) + 1

    async def latest_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRequestTable | None:
        result = await self._session.execute(
            select(ContentRequestTable)
            .where(
                ContentRequestTable.owner_id == owner_id,
                ContentRequestTable.project_id == project_id,
            )
            .order_by(ContentRequestTable.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ContentInputSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: ContentInputSnapshotTable) -> ContentInputSnapshotTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(
        self,
        snapshot_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentInputSnapshotTable | None:
        result = await self._session.execute(
            select(ContentInputSnapshotTable).where(
                ContentInputSnapshotTable.id == snapshot_id,
                ContentInputSnapshotTable.owner_id == owner_id,
                ContentInputSnapshotTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()


class ContentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: ContentRunTable) -> ContentRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: ContentRunTable) -> ContentRunTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRunTable | None:
        result = await self._session.execute(
            select(ContentRunTable).where(
                ContentRunTable.id == run_id,
                ContentRunTable.owner_id == owner_id,
                ContentRunTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_request(
        self,
        content_request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRunTable | None:
        result = await self._session.execute(
            select(ContentRunTable)
            .where(
                ContentRunTable.content_request_id == content_request_id,
                ContentRunTable.owner_id == owner_id,
                ContentRunTable.project_id == project_id,
                ContentRunTable.status.in_(list(_ACTIVE_RUN_STATUSES)),
            )
            .order_by(ContentRunTable.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self,
        content_request_id: UUID,
        idempotency_key: str,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRunTable | None:
        result = await self._session.execute(
            select(ContentRunTable)
            .where(
                ContentRunTable.content_request_id == content_request_id,
                ContentRunTable.idempotency_key == idempotency_key,
                ContentRunTable.owner_id == owner_id,
                ContentRunTable.project_id == project_id,
            )
            .order_by(ContentRunTable.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ContentRunCandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: ContentRunCandidateTable) -> ContentRunCandidateTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: ContentRunCandidateTable) -> ContentRunCandidateTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_for_run(
        self,
        content_run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ContentRunCandidateTable]:
        result = await self._session.execute(
            select(ContentRunCandidateTable)
            .where(
                ContentRunCandidateTable.content_run_id == content_run_id,
                ContentRunCandidateTable.owner_id == owner_id,
                ContentRunCandidateTable.project_id == project_id,
            )
            .order_by(ContentRunCandidateTable.candidate_index.asc())
        )
        return list(result.scalars().all())

    async def list_for_request(
        self,
        content_request_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ContentRunCandidateTable]:
        result = await self._session.execute(
            select(ContentRunCandidateTable)
            .where(
                ContentRunCandidateTable.content_request_id == content_request_id,
                ContentRunCandidateTable.owner_id == owner_id,
                ContentRunCandidateTable.project_id == project_id,
            )
            .order_by(
                ContentRunCandidateTable.created_at.desc(),
                ContentRunCandidateTable.candidate_index.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_asset(
        self,
        content_asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentRunCandidateTable | None:
        result = await self._session.execute(
            select(ContentRunCandidateTable).where(
                ContentRunCandidateTable.content_asset_id == content_asset_id,
                ContentRunCandidateTable.owner_id == owner_id,
                ContentRunCandidateTable.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

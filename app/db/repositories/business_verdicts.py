"""BusinessVerdict repositories (Commercial MVP P0.5)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.business_verdict import (
    BusinessVerdictEvidenceLinkTable,
    BusinessVerdictEvidenceSnapshotTable,
    BusinessVerdictTable,
)
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    BusinessVerdictConfidenceLevel,
    BusinessVerdictLifecycleStatus,
    VerdictKind,
)


class BusinessVerdictEvidenceSnapshotRepository(
    BaseRepository[BusinessVerdictEvidenceSnapshotTable]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BusinessVerdictEvidenceSnapshotTable)

    async def get_by_id_for_owner(
        self,
        snapshot_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessVerdictEvidenceSnapshotTable | None:
        statement = select(BusinessVerdictEvidenceSnapshotTable).where(
            BusinessVerdictEvidenceSnapshotTable.id == snapshot_id,
            BusinessVerdictEvidenceSnapshotTable.owner_id == owner_id,
            BusinessVerdictEvidenceSnapshotTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_reusable(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        snapshot_hash: str,
    ) -> BusinessVerdictEvidenceSnapshotTable | None:
        statement = select(BusinessVerdictEvidenceSnapshotTable).where(
            BusinessVerdictEvidenceSnapshotTable.owner_id == owner_id,
            BusinessVerdictEvidenceSnapshotTable.project_id == project_id,
            BusinessVerdictEvidenceSnapshotTable.investigation_id == investigation_id,
            BusinessVerdictEvidenceSnapshotTable.snapshot_hash == snapshot_hash,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


class BusinessVerdictRepository(BaseRepository[BusinessVerdictTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BusinessVerdictTable)

    async def get_by_id_for_owner(
        self,
        verdict_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessVerdictTable | None:
        statement = select(BusinessVerdictTable).where(
            BusinessVerdictTable.id == verdict_id,
            BusinessVerdictTable.owner_id == owner_id,
            BusinessVerdictTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def next_version(self, owner_id: UUID, project_id: UUID) -> int:
        statement = (
            select(BusinessVerdictTable.version)
            .where(
                BusinessVerdictTable.owner_id == owner_id,
                BusinessVerdictTable.project_id == project_id,
            )
            .order_by(desc(BusinessVerdictTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        current = result.scalar_one_or_none()
        return int(current or 0) + 1

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        verdict_type: VerdictKind | None = None,
        lifecycle_status: BusinessVerdictLifecycleStatus | None = None,
        confidence_level: BusinessVerdictConfidenceLevel | None = None,
        investigation_id: UUID | None = None,
        version: int | None = None,
        prepared_from: datetime | None = None,
        prepared_to: datetime | None = None,
        approved_from: datetime | None = None,
        approved_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BusinessVerdictTable]:
        statement = select(BusinessVerdictTable).where(
            BusinessVerdictTable.owner_id == owner_id,
            BusinessVerdictTable.project_id == project_id,
        )
        if verdict_type is not None:
            statement = statement.where(BusinessVerdictTable.verdict_type == verdict_type)
        if lifecycle_status is not None:
            statement = statement.where(
                BusinessVerdictTable.lifecycle_status == lifecycle_status
            )
        if confidence_level is not None:
            statement = statement.where(
                BusinessVerdictTable.confidence_level == confidence_level
            )
        if investigation_id is not None:
            statement = statement.where(
                BusinessVerdictTable.investigation_id == investigation_id
            )
        if version is not None:
            statement = statement.where(BusinessVerdictTable.version == version)
        if prepared_from is not None:
            statement = statement.where(BusinessVerdictTable.created_at >= prepared_from)
        if prepared_to is not None:
            statement = statement.where(BusinessVerdictTable.created_at <= prepared_to)
        if approved_from is not None:
            statement = statement.where(BusinessVerdictTable.approved_at >= approved_from)
        if approved_to is not None:
            statement = statement.where(BusinessVerdictTable.approved_at <= approved_to)
        statement = (
            statement.order_by(desc(BusinessVerdictTable.version))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def latest_approved(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessVerdictTable | None:
        statement = (
            select(BusinessVerdictTable)
            .where(
                BusinessVerdictTable.owner_id == owner_id,
                BusinessVerdictTable.project_id == project_id,
                BusinessVerdictTable.lifecycle_status
                == BusinessVerdictLifecycleStatus.APPROVED,
            )
            .order_by(desc(BusinessVerdictTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def latest_any(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessVerdictTable | None:
        statement = (
            select(BusinessVerdictTable)
            .where(
                BusinessVerdictTable.owner_id == owner_id,
                BusinessVerdictTable.project_id == project_id,
            )
            .order_by(desc(BusinessVerdictTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


class BusinessVerdictEvidenceLinkRepository(
    BaseRepository[BusinessVerdictEvidenceLinkTable]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BusinessVerdictEvidenceLinkTable)

    async def list_for_verdict(
        self,
        verdict_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[BusinessVerdictEvidenceLinkTable]:
        statement = select(BusinessVerdictEvidenceLinkTable).where(
            BusinessVerdictEvidenceLinkTable.verdict_id == verdict_id,
            BusinessVerdictEvidenceLinkTable.owner_id == owner_id,
            BusinessVerdictEvidenceLinkTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

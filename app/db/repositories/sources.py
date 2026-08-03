"""Source repositories (Commercial MVP P0.3)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import asc, desc, select

from app.db.models.source import InvestigationSourceLinkTable, SourceTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    InvestigationSourceLinkStatus,
    SourceFreshnessStatus,
    SourceProvenanceType,
    SourceReliabilityLevel,
    SourceStatus,
    SourceType,
)


class SourceRepository(BaseRepository[SourceTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SourceTable)

    async def get_by_id_for_owner(
        self,
        source_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> SourceTable | None:
        statement = select(SourceTable).where(
            SourceTable.id == source_id,
            SourceTable.owner_id == owner_id,
            SourceTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_live_by_fingerprint(
        self,
        owner_id: UUID,
        project_id: UUID,
        fingerprint: str,
    ) -> SourceTable | None:
        statement = select(SourceTable).where(
            SourceTable.owner_id == owner_id,
            SourceTable.project_id == project_id,
            SourceTable.fingerprint == fingerprint,
            SourceTable.status.notin_(
                (SourceStatus.SUPERSEDED, SourceStatus.ARCHIVED, SourceStatus.REJECTED)
            ),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        source_type: SourceType | None = None,
        provenance_type: SourceProvenanceType | None = None,
        freshness_status: SourceFreshnessStatus | None = None,
        reliability_level: SourceReliabilityLevel | None = None,
        status: SourceStatus | None = None,
        publisher: str | None = None,
        domain: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SourceTable]:
        statement = select(SourceTable).where(
            SourceTable.owner_id == owner_id,
            SourceTable.project_id == project_id,
        )
        if source_type is not None:
            statement = statement.where(SourceTable.source_type == source_type)
        if provenance_type is not None:
            statement = statement.where(SourceTable.provenance_type == provenance_type)
        if freshness_status is not None:
            statement = statement.where(SourceTable.freshness_status == freshness_status)
        if reliability_level is not None:
            statement = statement.where(SourceTable.reliability_level == reliability_level)
        if status is not None:
            statement = statement.where(SourceTable.status == status)
        if publisher:
            statement = statement.where(SourceTable.publisher == publisher)
        if domain:
            statement = statement.where(SourceTable.domain == domain)
        statement = (
            statement.order_by(desc(SourceTable.created_at)).offset(offset).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_versions(
        self,
        owner_id: UUID,
        project_id: UUID,
        source_id: UUID,
    ) -> list[SourceTable]:
        root = await self.get_by_id_for_owner(source_id, owner_id, project_id)
        if root is None:
            return []
        # Walk backward then collect superseding chain via fingerprint + lineage
        lineage: list[SourceTable] = [root]
        current = root
        while current.supersedes_source_id is not None:
            prev = await self.get_by_id_for_owner(
                current.supersedes_source_id,
                owner_id,
                project_id,
            )
            if prev is None:
                break
            lineage.append(prev)
            current = prev
        # Also find later versions that supersede any in lineage
        ids = {row.id for row in lineage}
        statement = select(SourceTable).where(
            SourceTable.owner_id == owner_id,
            SourceTable.project_id == project_id,
            SourceTable.supersedes_source_id.in_(ids),
        )
        result = await self.session.execute(statement)
        for row in result.scalars().all():
            if row.id not in ids:
                lineage.append(row)
                ids.add(row.id)
        lineage.sort(key=lambda r: r.version)
        return lineage


class InvestigationSourceLinkRepository(BaseRepository[InvestigationSourceLinkTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvestigationSourceLinkTable)

    async def get_link(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
    ) -> InvestigationSourceLinkTable | None:
        statement = select(InvestigationSourceLinkTable).where(
            InvestigationSourceLinkTable.owner_id == owner_id,
            InvestigationSourceLinkTable.project_id == project_id,
            InvestigationSourceLinkTable.investigation_id == investigation_id,
            InvestigationSourceLinkTable.source_id == source_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_investigation(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        *,
        status: InvestigationSourceLinkStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvestigationSourceLinkTable]:
        statement = select(InvestigationSourceLinkTable).where(
            InvestigationSourceLinkTable.owner_id == owner_id,
            InvestigationSourceLinkTable.project_id == project_id,
            InvestigationSourceLinkTable.investigation_id == investigation_id,
        )
        if status is not None:
            statement = statement.where(InvestigationSourceLinkTable.status == status)
        statement = (
            statement.order_by(asc(InvestigationSourceLinkTable.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

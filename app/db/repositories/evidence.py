"""Evidence repositories (Commercial MVP P0.4)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.evidence import EvidenceSourceLinkTable, InvestigationEvidenceTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceInvestigationArea,
    EvidenceLifecycleStatus,
    EvidenceMateriality,
    EvidenceType,
)


class EvidenceRepository(BaseRepository[InvestigationEvidenceTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvestigationEvidenceTable)

    async def get_by_id_for_owner(
        self,
        evidence_id: UUID,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> InvestigationEvidenceTable | None:
        statement = select(InvestigationEvidenceTable).where(
            InvestigationEvidenceTable.id == evidence_id,
            InvestigationEvidenceTable.owner_id == owner_id,
            InvestigationEvidenceTable.project_id == project_id,
            InvestigationEvidenceTable.investigation_id == investigation_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, evidence_id: UUID) -> InvestigationEvidenceTable | None:
        statement = select(InvestigationEvidenceTable).where(
            InvestigationEvidenceTable.id == evidence_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_live_by_fingerprint(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        fingerprint: str,
    ) -> InvestigationEvidenceTable | None:
        statement = select(InvestigationEvidenceTable).where(
            InvestigationEvidenceTable.owner_id == owner_id,
            InvestigationEvidenceTable.project_id == project_id,
            InvestigationEvidenceTable.investigation_id == investigation_id,
            InvestigationEvidenceTable.input_fingerprint == fingerprint,
            InvestigationEvidenceTable.lifecycle_status.notin_(
                (
                    EvidenceLifecycleStatus.SUPERSEDED,
                    EvidenceLifecycleStatus.ARCHIVED,
                    EvidenceLifecycleStatus.REJECTED,
                )
            ),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_investigation(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        *,
        lifecycle_status: EvidenceLifecycleStatus | None = None,
        assessment_state: EvidenceAssessmentState | None = None,
        confidence_level: EvidenceConfidenceLevel | None = None,
        materiality: EvidenceMateriality | None = None,
        evidence_type: EvidenceType | None = None,
        investigation_area: EvidenceInvestigationArea | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvestigationEvidenceTable]:
        statement = select(InvestigationEvidenceTable).where(
            InvestigationEvidenceTable.owner_id == owner_id,
            InvestigationEvidenceTable.project_id == project_id,
            InvestigationEvidenceTable.investigation_id == investigation_id,
        )
        if lifecycle_status is not None:
            statement = statement.where(
                InvestigationEvidenceTable.lifecycle_status == lifecycle_status
            )
        if assessment_state is not None:
            statement = statement.where(
                InvestigationEvidenceTable.assessment_state == assessment_state
            )
        if confidence_level is not None:
            statement = statement.where(
                InvestigationEvidenceTable.confidence_level == confidence_level
            )
        if materiality is not None:
            statement = statement.where(
                InvestigationEvidenceTable.materiality == materiality
            )
        if evidence_type is not None:
            statement = statement.where(
                InvestigationEvidenceTable.evidence_type == evidence_type
            )
        if investigation_area is not None:
            statement = statement.where(
                InvestigationEvidenceTable.investigation_area == investigation_area
            )
        statement = (
            statement.order_by(desc(InvestigationEvidenceTable.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_all_for_summary(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> list[InvestigationEvidenceTable]:
        statement = select(InvestigationEvidenceTable).where(
            InvestigationEvidenceTable.owner_id == owner_id,
            InvestigationEvidenceTable.project_id == project_id,
            InvestigationEvidenceTable.investigation_id == investigation_id,
            InvestigationEvidenceTable.lifecycle_status.notin_(
                (EvidenceLifecycleStatus.SUPERSEDED, EvidenceLifecycleStatus.ARCHIVED)
            ),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


class EvidenceSourceLinkRepository(BaseRepository[EvidenceSourceLinkTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvidenceSourceLinkTable)

    async def list_for_evidence(
        self,
        evidence_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[EvidenceSourceLinkTable]:
        statement = select(EvidenceSourceLinkTable).where(
            EvidenceSourceLinkTable.evidence_id == evidence_id,
            EvidenceSourceLinkTable.owner_id == owner_id,
            EvidenceSourceLinkTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_link(
        self,
        evidence_id: UUID,
        source_id: UUID,
        owner_id: UUID,
        project_id: UUID,
        stance: str | None = None,
    ) -> EvidenceSourceLinkTable | None:
        statement = select(EvidenceSourceLinkTable).where(
            EvidenceSourceLinkTable.evidence_id == evidence_id,
            EvidenceSourceLinkTable.source_id == source_id,
            EvidenceSourceLinkTable.owner_id == owner_id,
            EvidenceSourceLinkTable.project_id == project_id,
        )
        if stance is not None:
            statement = statement.where(EvidenceSourceLinkTable.stance == stance)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete_for_evidence(self, evidence_id: UUID) -> None:
        statement = select(EvidenceSourceLinkTable).where(
            EvidenceSourceLinkTable.evidence_id == evidence_id,
        )
        result = await self.session.execute(statement)
        for row in result.scalars().all():
            await self.session.delete(row)

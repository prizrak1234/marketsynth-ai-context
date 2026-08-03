"""Immutable KnowledgeSnapshot persistence (Phase H2.5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeSnapshotTable
from app.knowledge_foundation.retrieval_adapter import (
    RETRIEVAL_POLICY_VERSION,
    compute_snapshot_hash,
)
from app.schemas.contracts import (
    KnowledgeAuthority,
    KnowledgeRetrievalResult,
    KnowledgeSnapshot,
    KnowledgeSnapshotItemRef,
)


def result_to_item_refs(result: KnowledgeRetrievalResult) -> list[dict]:
    refs: list[dict] = []
    for item in result.items:
        refs.append(
            {
                "knowledge_item_id": str(item.knowledge_item_id),
                "code": item.code,
                "version": item.version,
                "content_hash": item.content_hash,
                "relevance_reason": item.relevance_reason,
                "authority": item.authority.value,
                "citation_required": item.citation_required,
            }
        )
    return refs


class KnowledgeSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_from_retrieval(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        skill_code: str,
        skill_version: str,
        capability_pack_version: str,
        locale: str,
        retrieval: KnowledgeRetrievalResult,
    ) -> KnowledgeSnapshotTable:
        refs = result_to_item_refs(retrieval)
        snap_hash = compute_snapshot_hash(
            skill_code=skill_code,
            skill_version=skill_version,
            capability_pack_version=capability_pack_version,
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            locale=locale,
            item_refs=refs,
        )
        row = KnowledgeSnapshotTable(
            owner_id=owner_id,
            project_id=project_id,
            skill_code=skill_code,
            skill_version=skill_version,
            capability_pack_version=capability_pack_version,
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            locale=locale,
            item_refs=refs,
            snapshot_hash=snap_hash,
            created_at=utc_now(),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_for_owner(
        self,
        owner_id: UUID,
        snapshot_id: UUID,
    ) -> KnowledgeSnapshotTable | None:
        stmt = select(KnowledgeSnapshotTable).where(
            KnowledgeSnapshotTable.id == snapshot_id,
            KnowledgeSnapshotTable.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def to_contract(self, row: KnowledgeSnapshotTable) -> KnowledgeSnapshot:
        refs = [
            KnowledgeSnapshotItemRef(
                knowledge_item_id=UUID(str(ref["knowledge_item_id"])),
                code=ref["code"],
                version=ref["version"],
                content_hash=ref["content_hash"],
                relevance_reason=ref.get("relevance_reason", ""),
                authority=KnowledgeAuthority(ref["authority"])
                if isinstance(ref["authority"], str)
                else ref["authority"],
                citation_required=bool(ref.get("citation_required", False)),
            )
            for ref in (row.item_refs or [])
        ]
        return KnowledgeSnapshot(
            id=row.id,
            owner_id=row.owner_id,
            project_id=row.project_id,
            skill_code=row.skill_code,
            skill_version=row.skill_version,
            capability_pack_version=row.capability_pack_version,
            retrieval_policy_version=row.retrieval_policy_version,
            locale=row.locale,
            item_refs=refs,
            snapshot_hash=row.snapshot_hash,
            created_at=row.created_at,
        )

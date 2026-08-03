"""Durable knowledge store — CRUD, approve, supersede (immutable approved versions)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeItemTable
from app.schemas.contracts import (
    KnowledgeItemStatus,
    StoredKnowledgeItem,
)


class KnowledgeStoreError(ValueError):
    pass


def content_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def row_to_stored(row: KnowledgeItemTable) -> StoredKnowledgeItem:
    return StoredKnowledgeItem(
        id=row.id,
        code=row.code,
        title=row.title,
        knowledge_type=row.knowledge_type,
        domain=row.domain,
        content=row.content,
        content_format=row.content_format,
        content_hash=row.content_hash,
        source_uri=row.source_uri,
        source_hash=row.source_hash,
        version=row.version,
        status=row.status,
        authority=row.authority,
        tenant_scope=row.tenant_scope,
        owner_id=row.owner_id,
        project_id=row.project_id,
        locale=row.locale,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        supersedes_id=row.supersedes_id,
        citation_required=row.citation_required,
        tags=list(row.tags or []),
        specialist_roles=list(row.specialist_roles or []),
        metadata=dict(row.metadata_json or {}),
        review_rationale=row.review_rationale,
        created_at=row.created_at,
        reviewed_at=row.reviewed_at,
        reviewed_by=row.reviewed_by,
    )


class KnowledgeStoreService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, item_id: UUID) -> KnowledgeItemTable | None:
        return await self._session.get(KnowledgeItemTable, item_id)

    async def get_by_code_version(
        self,
        code: str,
        version: str,
    ) -> KnowledgeItemTable | None:
        stmt = select(KnowledgeItemTable).where(
            KnowledgeItemTable.code == code,
            KnowledgeItemTable.version == version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_items(
        self,
        *,
        status: KnowledgeItemStatus | None = None,
        domain: str | None = None,
        locale: str | None = None,
        limit: int = 200,
    ) -> list[KnowledgeItemTable]:
        stmt = select(KnowledgeItemTable).order_by(
            KnowledgeItemTable.code,
            KnowledgeItemTable.version,
        )
        if status is not None:
            stmt = stmt.where(KnowledgeItemTable.status == status)
        if domain is not None:
            stmt = stmt.where(KnowledgeItemTable.domain == domain)
        if locale is not None:
            stmt = stmt.where(KnowledgeItemTable.locale == locale)
        stmt = stmt.limit(min(max(limit, 1), 500))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def approve(
        self,
        item_id: UUID,
        *,
        reviewed_by: str,
        rationale: str | None = None,
    ) -> KnowledgeItemTable:
        row = await self.get_by_id(item_id)
        if row is None:
            raise KnowledgeStoreError(f"unknown_item:{item_id}")
        if row.status == KnowledgeItemStatus.APPROVED:
            return row
        if row.status not in {
            KnowledgeItemStatus.CANDIDATE,
            KnowledgeItemStatus.UNDER_REVIEW,
        }:
            raise KnowledgeStoreError(f"cannot_approve:{row.status.value}")
        row.status = KnowledgeItemStatus.APPROVED
        row.reviewed_at = utc_now()
        row.reviewed_by = reviewed_by[:128]
        row.review_rationale = (rationale or "")[:2000] or None
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def reject(
        self,
        item_id: UUID,
        *,
        reviewed_by: str,
        rationale: str | None = None,
    ) -> KnowledgeItemTable:
        row = await self.get_by_id(item_id)
        if row is None:
            raise KnowledgeStoreError(f"unknown_item:{item_id}")
        if row.status in {KnowledgeItemStatus.SUPERSEDED, KnowledgeItemStatus.ARCHIVED}:
            raise KnowledgeStoreError(f"cannot_reject:{row.status.value}")
        row.status = KnowledgeItemStatus.REJECTED
        row.reviewed_at = utc_now()
        row.reviewed_by = reviewed_by[:128]
        row.review_rationale = (rationale or "")[:2000] or None
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def archive(
        self,
        item_id: UUID,
        *,
        reviewed_by: str,
        rationale: str | None = None,
    ) -> KnowledgeItemTable:
        row = await self.get_by_id(item_id)
        if row is None:
            raise KnowledgeStoreError(f"unknown_item:{item_id}")
        row.status = KnowledgeItemStatus.ARCHIVED
        row.reviewed_at = utc_now()
        row.reviewed_by = reviewed_by[:128]
        row.review_rationale = (rationale or "")[:2000] or None
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def supersede(
        self,
        item_id: UUID,
        *,
        content: str,
        version: str,
        reviewed_by: str,
        source_uri: str | None = None,
        source_hash: str | None = None,
        rationale: str | None = None,
        locale: str | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeItemTable:
        """Create a new immutable version; mark previous approved row superseded."""
        old = await self.get_by_id(item_id)
        if old is None:
            raise KnowledgeStoreError(f"unknown_item:{item_id}")
        if old.status != KnowledgeItemStatus.APPROVED:
            raise KnowledgeStoreError("supersede_requires_approved")
        existing = await self.get_by_code_version(old.code, version)
        if existing is not None:
            raise KnowledgeStoreError(f"version_exists:{old.code}:{version}")
        if content == old.content and version == old.version:
            raise KnowledgeStoreError("no_inplace_overwrite")

        now = utc_now()
        new_row = KnowledgeItemTable(
            code=old.code,
            title=old.title,
            knowledge_type=old.knowledge_type,
            domain=old.domain,
            content=content,
            content_format=old.content_format,
            content_hash=content_hash(content),
            source_uri=source_uri or old.source_uri,
            source_hash=source_hash or old.source_hash,
            version=version,
            status=KnowledgeItemStatus.APPROVED,
            authority=old.authority,
            tenant_scope=old.tenant_scope,
            owner_id=old.owner_id,
            project_id=old.project_id,
            locale=locale or old.locale,
            valid_from=now,
            valid_until=None,
            supersedes_id=old.id,
            citation_required=old.citation_required,
            tags=list(tags if tags is not None else (old.tags or [])),
            specialist_roles=list(old.specialist_roles or []),
            metadata_json=dict(old.metadata_json or {}),
            review_rationale=(rationale or "")[:2000] or None,
            created_at=now,
            reviewed_at=now,
            reviewed_by=reviewed_by[:128],
        )
        old.status = KnowledgeItemStatus.SUPERSEDED
        old.valid_until = now
        old.reviewed_at = now
        old.reviewed_by = reviewed_by[:128]
        self._session.add(old)
        self._session.add(new_row)
        await self._session.commit()
        await self._session.refresh(new_row)
        return new_row

    def assert_not_mutating_approved_content(
        self,
        row: KnowledgeItemTable,
        *,
        new_content: str,
    ) -> None:
        if (
            row.status == KnowledgeItemStatus.APPROVED
            and new_content != row.content
        ):
            raise KnowledgeStoreError("approved_version_immutable")

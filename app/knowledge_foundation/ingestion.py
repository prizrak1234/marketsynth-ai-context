"""Ingest curated Pack A–D into durable storage — no recursive docs scan."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeItemTable
from app.knowledge_foundation.approved_content_pack import (
    INGESTION_MANIFEST_V1,
    PackSeed,
    approved_content_pack_seeds,
)
from app.knowledge_foundation.store import KnowledgeStoreService, content_hash
from app.schemas.contracts import KnowledgeItemStatus


async def ingest_approved_content_pack(
    session: AsyncSession,
    *,
    reviewed_by: str = "h2.3_curated_pack",
) -> list[KnowledgeItemTable]:
    """Idempotent insert of Pack A–D. Never overwrites an existing approved version."""
    store = KnowledgeStoreService(session)
    created: list[KnowledgeItemTable] = []
    now = utc_now()
    for seed in approved_content_pack_seeds():
        existing = await store.get_by_code_version(seed.code, seed.version)
        if existing is not None:
            created.append(existing)
            continue
        row = _seed_to_row(seed, reviewed_by=reviewed_by, now=now)
        session.add(row)
        created.append(row)
    await session.commit()
    for row in created:
        await session.refresh(row)
    return created


def _seed_to_row(
    seed: PackSeed,
    *,
    reviewed_by: str,
    now,
) -> KnowledgeItemTable:
    return KnowledgeItemTable(
        code=seed.code,
        title=seed.title,
        knowledge_type=seed.knowledge_type,
        domain=seed.domain,
        content=seed.content,
        content_format=seed.content_format,
        content_hash=content_hash(seed.content),
        source_uri=seed.source_uri,
        source_hash=seed.source_hash,
        version=seed.version,
        status=KnowledgeItemStatus.APPROVED,
        authority=seed.authority,
        tenant_scope=seed.tenant_scope,
        owner_id=None,
        project_id=None,
        locale=seed.locale,
        valid_from=now,
        valid_until=None,
        supersedes_id=None,
        citation_required=seed.citation_required,
        tags=list(seed.tags),
        specialist_roles=list(seed.specialist_roles),
        metadata_json={"pack": seed.pack, **(seed.metadata or {})},
        review_rationale=f"Ingested Pack {seed.pack} curated foundation",
        created_at=now,
        reviewed_at=now,
        reviewed_by=reviewed_by[:128],
    )


def ingestion_manifest_v1() -> list[dict]:
    return list(INGESTION_MANIFEST_V1)

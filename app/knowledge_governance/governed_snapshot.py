"""KG.2 — Governed Knowledge Snapshot for specialist runtime (no VectorDB)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_governance import (
    KnowledgeAuditEventTable,
    KnowledgeVersionTable,
    SemanticChunkTable,
)
from app.db.models.knowledge_item import KnowledgeSnapshotTable
from app.domain.knowledge_governance import evaluate_knowledge_freshness
from app.knowledge_foundation.retrieval_adapter import RETRIEVAL_POLICY_VERSION
from app.schemas.contracts import KnowledgeGovernanceStatus


class InsufficientGovernedKnowledgeError(Exception):
    def __init__(self, message: str = "insufficient_governed_knowledge") -> None:
        self.code = "insufficient_governed_knowledge"
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def list_eligible_published_versions(
    session: AsyncSession,
    *,
    tenant_owner_id: UUID,
    domain: str | None = None,
) -> list[KnowledgeVersionTable]:
    """Admission: published + not expired + owner tenant."""
    stmt = select(KnowledgeVersionTable).where(
        KnowledgeVersionTable.tenant_owner_id == tenant_owner_id,
        KnowledgeVersionTable.status == KnowledgeGovernanceStatus.PUBLISHED,
        KnowledgeVersionTable.archived_at.is_(None),
    )
    result = await session.execute(stmt)
    eligible: list[KnowledgeVersionTable] = []
    for ver in result.scalars().all():
        if ver.owner_user_id is None:
            continue
        check = evaluate_knowledge_freshness(
            knowledge_id=ver.id,
            status=ver.status,
            review_date=ver.review_date,
            next_review=ver.next_review_at,
        )
        if check.expired:
            continue
        if domain and str(ver.domain.value if hasattr(ver.domain, "value") else ver.domain) != domain:
            # soft filter — still allow OPERATIONS / MIXED
            d = str(ver.domain.value if hasattr(ver.domain, "value") else ver.domain)
            if d not in {domain, "operations", "mixed", "product"}:
                continue
        eligible.append(ver)
    return eligible


async def create_governed_snapshot(
    session: AsyncSession,
    *,
    tenant_owner_id: UUID,
    skill_code: str,
    skill_version: str = "1.0",
    capability_pack_version: str = "1.0",
    locale: str = "ru",
    require_knowledge: bool = True,
    domain: str | None = None,
) -> KnowledgeSnapshotTable:
    """
    UserRequest → skill → filter → published/current → immutable KnowledgeSnapshot.
    Blocks when require_knowledge and no eligible versions.
    """
    versions = await list_eligible_published_versions(
        session, tenant_owner_id=tenant_owner_id, domain=domain
    )
    if require_knowledge and not versions:
        session.add(
            KnowledgeAuditEventTable(
                id=uuid4(),
                tenant_owner_id=tenant_owner_id,
                event_type="knowledge.execution_blocked",
                actor_user_id=tenant_owner_id,
                payload={"reason": "insufficient_governed_knowledge", "skill_code": skill_code},
                created_at=_now(),
            )
        )
        await session.commit()
        raise InsufficientGovernedKnowledgeError(
            "Для навыка нет опубликованных актуальных знаний (insufficient_governed_knowledge)."
        )

    version_ids = [str(v.id) for v in versions]
    chunk_ids: list[str] = []
    source_ids: list[str] = []
    item_refs: list[dict[str, Any]] = []
    freshness_summary = {"fresh": 0, "due_for_review": 0, "expired_excluded": 0}

    for ver in versions:
        check = evaluate_knowledge_freshness(
            knowledge_id=ver.id,
            status=ver.status,
            review_date=ver.review_date,
            next_review=ver.next_review_at,
        )
        if check.freshness.value == "due_for_review":
            freshness_summary["due_for_review"] += 1
        else:
            freshness_summary["fresh"] += 1
        source_ids.append(ver.source_uri)
        ch = await session.execute(
            select(SemanticChunkTable).where(SemanticChunkTable.version_id == ver.id)
        )
        for c in ch.scalars().all():
            chunk_ids.append(str(c.id))
        item_refs.append(
            {
                "knowledge_item_id": str(ver.id),  # governance version id in snapshot slot
                "knowledge_version_id": str(ver.id),
                "object_id": str(ver.object_id),
                "code": f"kg:{ver.object_id}:{ver.version}",
                "version": ver.version,
                "content_hash": ver.content_hash,
                "relevance_reason": "governed_published",
                "authority": "product",
                "citation_required": bool(ver.citation_required),
                "source_uri": ver.source_uri,
            }
        )

    governance_meta = {
        "knowledge_version_ids": version_ids,
        "chunk_ids": chunk_ids,
        "source_ids": source_ids,
        "freshness_summary": freshness_summary,
        "policy_decision": "published_and_fresh_only",
        "policy_version": "kg.2",
        "tenant_owner_id": str(tenant_owner_id),
    }
    snap_hash = _hash(
        {
            "skill_code": skill_code,
            "skill_version": skill_version,
            "locale": locale,
            "item_refs": item_refs,
            "governance_meta": governance_meta,
            "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
        }
    )
    row = KnowledgeSnapshotTable(
        owner_id=tenant_owner_id,
        project_id=None,
        skill_code=skill_code,
        skill_version=skill_version,
        capability_pack_version=capability_pack_version,
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        locale=locale,
        item_refs=item_refs,
        snapshot_hash=snap_hash,
        created_at=utc_now(),
        governance_meta=governance_meta,
    )
    session.add(row)
    session.add(
        KnowledgeAuditEventTable(
            id=uuid4(),
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.snapshot_created",
            actor_user_id=tenant_owner_id,
            payload={
                "snapshot_hash": snap_hash,
                "version_count": len(version_ids),
                "skill_code": skill_code,
            },
            created_at=_now(),
        )
    )
    await session.commit()
    await session.refresh(row)
    return row

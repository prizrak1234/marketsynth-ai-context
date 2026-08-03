"""KG.2 — Operator service: candidates, review, publish, freshness, audit."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_governance import (
    KnowledgeAuditEventTable,
    KnowledgeFreshnessCheckTable,
    KnowledgeObjectTable,
    KnowledgeOwnershipTable,
    KnowledgeReviewTable,
    KnowledgeVersionTable,
    SemanticChunkTable,
)
from app.domain.knowledge_governance import evaluate_knowledge_freshness
from app.knowledge_governance.lifecycle import (
    LifecycleError,
    assert_publish_requirements,
    assert_transition,
)
from app.schemas.contracts import (
    KnowledgeConfidenceLevel,
    KnowledgeDomain,
    KnowledgeFreshnessState,
    KnowledgeGovernanceStatus,
    KnowledgeVisibility,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_content(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def semantic_chunk_from_sections(
    *,
    content: str,
    domain: KnowledgeDomain,
    language: str,
    source_uri: str,
    source_hash: str | None,
) -> list[dict[str, Any]]:
    """Structure-aware chunking: split on markdown headings / numbered rules — not fixed chars."""
    parts = re.split(r"(?m)^(#{1,3}\s+.+|[0-9]+\.\s+.+)$", content)
    blocks: list[str] = []
    buf = ""
    for part in parts:
        if not part:
            continue
        if re.match(r"(?m)^(#{1,3}\s+|[0-9]+\.\s+)", part):
            if buf.strip():
                blocks.append(buf.strip())
            buf = part
        else:
            buf += part
    if buf.strip():
        blocks.append(buf.strip())
    if not blocks:
        blocks = [content.strip() or "empty"]

    chunks: list[dict[str, Any]] = []
    for i, block in enumerate(blocks[:40]):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        title = lines[0][:200] if lines else f"Chunk {i + 1}"
        body = "\n".join(lines[1:]) if len(lines) > 1 else block
        chunks.append(
            {
                "title": title.lstrip("#").strip()[:500],
                "intent": f"Convey governed rule/section: {title[:120]}",
                "rule": body[:4000] or title,
                "condition": None,
                "exception": None,
                "references": [source_uri] if source_uri else [],
                "source_location": f"section:{i + 1}",
                "source_hash": source_hash,
                "language": language,
                "domain": domain,
            }
        )
    return chunks


class KnowledgeGovernanceOperator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _audit(
        self,
        *,
        tenant_owner_id: UUID,
        event_type: str,
        actor_user_id: UUID | None,
        object_id: UUID | None = None,
        version_id: UUID | None = None,
        payload: dict | None = None,
    ) -> None:
        self._session.add(
            KnowledgeAuditEventTable(
                id=uuid4(),
                tenant_owner_id=tenant_owner_id,
                event_type=event_type,
                object_id=object_id,
                version_id=version_id,
                actor_user_id=actor_user_id,
                payload=payload or {},
                created_at=_now(),
            )
        )

    async def create_candidate(
        self,
        *,
        tenant_owner_id: UUID,
        actor_user_id: UUID,
        code: str,
        title: str,
        content: str,
        source_uri: str,
        domain: KnowledgeDomain = KnowledgeDomain.OPERATIONS,
        language: str = "ru",
        source_hash: str | None = None,
        citation_required: bool = True,
    ) -> dict:
        existing = await self._session.execute(
            select(KnowledgeObjectTable).where(
                KnowledgeObjectTable.tenant_owner_id == tenant_owner_id,
                KnowledgeObjectTable.code == code,
            )
        )
        if existing.scalar_one_or_none():
            raise LifecycleError("code_exists", "Knowledge object code already exists")

        obj_id = uuid4()
        ver_id = uuid4()
        content_hash = _hash_content(content)
        obj = KnowledgeObjectTable(
            id=obj_id,
            tenant_owner_id=tenant_owner_id,
            code=code[:128],
            title=title[:500],
            domain=domain,
            visibility=KnowledgeVisibility.OWNER,
            status=KnowledgeGovernanceStatus.DRAFT,
            current_version_id=ver_id,
            created_at=_now(),
            updated_at=_now(),
            metadata_json={},
        )
        ver = KnowledgeVersionTable(
            id=ver_id,
            object_id=obj_id,
            tenant_owner_id=tenant_owner_id,
            version="1.0",
            status=KnowledgeGovernanceStatus.DRAFT,
            content=content,
            content_hash=content_hash,
            source_uri=source_uri[:1000],
            source_hash=source_hash,
            language=language,
            domain=domain,
            confidence=KnowledgeConfidenceLevel.UNVERIFIED,
            freshness=KnowledgeFreshnessState.UNKNOWN,
            citation_required=citation_required,
            lock_version=1,
            created_at=_now(),
            evidence_chain=[],
            decision_chain=[
                {
                    "decision_id": str(uuid4()),
                    "decision_type": "candidate_created",
                    "actor": str(actor_user_id),
                    "decided_at": _now().isoformat(),
                }
            ],
        )
        self._session.add(obj)
        self._session.add(ver)
        # Semantic chunks
        for ch in semantic_chunk_from_sections(
            content=content,
            domain=domain,
            language=language,
            source_uri=source_uri,
            source_hash=source_hash or content_hash,
        ):
            self._session.add(
                SemanticChunkTable(
                    id=uuid4(),
                    version_id=ver_id,
                    object_id=obj_id,
                    tenant_owner_id=tenant_owner_id,
                    title=ch["title"],
                    intent=ch["intent"],
                    rule=ch["rule"],
                    condition=ch.get("condition"),
                    exception=ch.get("exception"),
                    references_json=ch.get("references") or [],
                    source_location=ch.get("source_location"),
                    source_hash=ch.get("source_hash"),
                    language=language,
                    domain=domain,
                    created_at=_now(),
                )
            )
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.candidate_created",
            actor_user_id=actor_user_id,
            object_id=obj_id,
            version_id=ver_id,
        )
        await self._session.commit()
        return {"object_id": str(obj_id), "version_id": str(ver_id), "status": "draft"}

    async def assign_owner(
        self,
        *,
        tenant_owner_id: UUID,
        actor_user_id: UUID,
        object_id: UUID,
        owner_user_id: UUID,
        reviewer_user_id: UUID | None = None,
    ) -> dict:
        obj = await self._get_object(tenant_owner_id, object_id)
        own = await self._session.execute(
            select(KnowledgeOwnershipTable).where(
                KnowledgeOwnershipTable.object_id == object_id
            )
        )
        row = own.scalar_one_or_none()
        if row is None:
            row = KnowledgeOwnershipTable(
                id=uuid4(),
                object_id=object_id,
                tenant_owner_id=tenant_owner_id,
                owner_user_id=owner_user_id,
                reviewer_user_id=reviewer_user_id,
                assigned_at=_now(),
                assigned_by=actor_user_id,
            )
            self._session.add(row)
        else:
            row.owner_user_id = owner_user_id
            row.reviewer_user_id = reviewer_user_id
            row.assigned_at = _now()
            row.assigned_by = actor_user_id
            self._session.add(row)

        if obj.current_version_id:
            ver = await self._session.get(KnowledgeVersionTable, obj.current_version_id)
            if ver and ver.tenant_owner_id == tenant_owner_id:
                ver.owner_user_id = owner_user_id
                if reviewer_user_id:
                    ver.reviewer_user_id = reviewer_user_id
                self._session.add(ver)

        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.owner_assigned",
            actor_user_id=actor_user_id,
            object_id=object_id,
            payload={"owner_user_id": str(owner_user_id)},
        )
        await self._session.commit()
        return {"object_id": str(object_id), "owner_user_id": str(owner_user_id)}

    async def review_version(
        self,
        *,
        tenant_owner_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
        decision: str,
        rationale: str | None = None,
        next_review_days: int = 90,
    ) -> dict:
        ver = await self._get_version(tenant_owner_id, version_id)
        decision_n = (decision or "").strip().lower()
        if decision_n not in {"approve", "reject", "request_changes"}:
            raise LifecycleError("invalid_review_decision", "decision must be approve|reject|request_changes")

        self._session.add(
            KnowledgeReviewTable(
                id=uuid4(),
                version_id=version_id,
                object_id=ver.object_id,
                tenant_owner_id=tenant_owner_id,
                reviewer_user_id=actor_user_id,
                decision=decision_n,
                rationale=(rationale or "")[:4000] or None,
                created_at=_now(),
            )
        )
        ver.reviewer_user_id = actor_user_id
        ver.review_date = _now()
        if decision_n == "approve":
            assert_transition(ver.status, KnowledgeGovernanceStatus.VALIDATED)
            ver.status = KnowledgeGovernanceStatus.VALIDATED
            ver.next_review_at = _now() + timedelta(days=max(7, next_review_days))
            ver.confidence = KnowledgeConfidenceLevel.MEDIUM
            event = "knowledge.validated"
        else:
            ver.status = KnowledgeGovernanceStatus.DRAFT
            event = "knowledge.review_rejected"
        chain = list(ver.decision_chain or [])
        chain.append(
            {
                "decision_id": str(uuid4()),
                "decision_type": decision_n,
                "actor": str(actor_user_id),
                "decided_at": _now().isoformat(),
                "rationale": rationale,
            }
        )
        ver.decision_chain = chain
        ver.lock_version = int(ver.lock_version or 1) + 1
        self._session.add(ver)
        obj = await self._get_object(tenant_owner_id, ver.object_id)
        obj.status = ver.status
        obj.updated_at = _now()
        self._session.add(obj)
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type=event,
            actor_user_id=actor_user_id,
            object_id=ver.object_id,
            version_id=version_id,
        )
        await self._session.commit()
        return {"version_id": str(version_id), "status": ver.status.value}

    async def publish_version(
        self,
        *,
        tenant_owner_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
        expected_lock_version: int | None = None,
    ) -> dict:
        ver = await self._get_version(tenant_owner_id, version_id)
        if expected_lock_version is not None and int(ver.lock_version) != int(
            expected_lock_version
        ):
            raise LifecycleError("optimistic_lock_conflict", "Version was modified")
        assert_transition(ver.status, KnowledgeGovernanceStatus.PUBLISHED)
        assert_publish_requirements(
            owner_user_id=ver.owner_user_id,
            reviewer_user_id=ver.reviewer_user_id,
            review_date=ver.review_date,
            next_review_at=ver.next_review_at,
            source_uri=ver.source_uri,
            content=ver.content,
        )
        # Immutable: do not rewrite content — only status/dates
        ver.status = KnowledgeGovernanceStatus.PUBLISHED
        ver.published_at = _now()
        ver.effective_from = ver.effective_from or _now()
        ver.freshness = KnowledgeFreshnessState.FRESH
        ver.lock_version = int(ver.lock_version or 1) + 1
        self._session.add(ver)
        obj = await self._get_object(tenant_owner_id, ver.object_id)
        obj.status = KnowledgeGovernanceStatus.PUBLISHED
        obj.current_version_id = ver.id
        obj.updated_at = _now()
        self._session.add(obj)
        await self._persist_freshness(ver)
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.published",
            actor_user_id=actor_user_id,
            object_id=ver.object_id,
            version_id=version_id,
        )
        await self._session.commit()
        return {"version_id": str(version_id), "status": "published"}

    async def deprecate_version(
        self, *, tenant_owner_id: UUID, actor_user_id: UUID, version_id: UUID
    ) -> dict:
        ver = await self._get_version(tenant_owner_id, version_id)
        assert_transition(ver.status, KnowledgeGovernanceStatus.DEPRECATED)
        ver.status = KnowledgeGovernanceStatus.DEPRECATED
        ver.freshness = KnowledgeFreshnessState.DEPRECATED
        ver.lock_version = int(ver.lock_version or 1) + 1
        self._session.add(ver)
        obj = await self._get_object(tenant_owner_id, ver.object_id)
        obj.status = KnowledgeGovernanceStatus.DEPRECATED
        obj.updated_at = _now()
        self._session.add(obj)
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.deprecated",
            actor_user_id=actor_user_id,
            object_id=ver.object_id,
            version_id=version_id,
        )
        await self._session.commit()
        return {"version_id": str(version_id), "status": "deprecated"}

    async def supersede_version(
        self,
        *,
        tenant_owner_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
        new_content: str,
        new_version: str,
        source_uri: str | None = None,
    ) -> dict:
        old = await self._get_version(tenant_owner_id, version_id)
        assert_transition(old.status, KnowledgeGovernanceStatus.SUPERSEDED)
        # Create new immutable version (draft) then leave old as superseded after publish of new
        # Spec: published → superseded with replacement_version_id
        new_id = uuid4()
        new_ver = KnowledgeVersionTable(
            id=new_id,
            object_id=old.object_id,
            tenant_owner_id=tenant_owner_id,
            version=new_version[:32],
            status=KnowledgeGovernanceStatus.DRAFT,
            content=new_content,
            content_hash=_hash_content(new_content),
            source_uri=(source_uri or old.source_uri)[:1000],
            source_hash=old.source_hash,
            language=old.language,
            domain=old.domain,
            confidence=KnowledgeConfidenceLevel.UNVERIFIED,
            freshness=KnowledgeFreshnessState.UNKNOWN,
            owner_user_id=old.owner_user_id,
            reviewer_user_id=None,
            citation_required=old.citation_required,
            supersedes_version_id=old.id,
            lock_version=1,
            created_at=_now(),
            evidence_chain=[],
            decision_chain=[],
        )
        self._session.add(new_ver)
        for ch in semantic_chunk_from_sections(
            content=new_content,
            domain=old.domain,
            language=old.language,
            source_uri=new_ver.source_uri,
            source_hash=new_ver.content_hash,
        ):
            self._session.add(
                SemanticChunkTable(
                    id=uuid4(),
                    version_id=new_id,
                    object_id=old.object_id,
                    tenant_owner_id=tenant_owner_id,
                    title=ch["title"],
                    intent=ch["intent"],
                    rule=ch["rule"],
                    condition=ch.get("condition"),
                    exception=ch.get("exception"),
                    references_json=ch.get("references") or [],
                    source_location=ch.get("source_location"),
                    source_hash=ch.get("source_hash"),
                    language=old.language,
                    domain=old.domain,
                    created_at=_now(),
                )
            )
        old.status = KnowledgeGovernanceStatus.SUPERSEDED
        old.replacement_version_id = new_id
        old.lock_version = int(old.lock_version or 1) + 1
        self._session.add(old)
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.superseded",
            actor_user_id=actor_user_id,
            object_id=old.object_id,
            version_id=version_id,
            payload={"replacement_version_id": str(new_id)},
        )
        await self._session.commit()
        return {
            "superseded_version_id": str(version_id),
            "replacement_version_id": str(new_id),
            "replacement_status": "draft",
        }

    async def archive_version(
        self, *, tenant_owner_id: UUID, actor_user_id: UUID, version_id: UUID
    ) -> dict:
        ver = await self._get_version(tenant_owner_id, version_id)
        assert_transition(ver.status, KnowledgeGovernanceStatus.ARCHIVED)
        ver.status = KnowledgeGovernanceStatus.ARCHIVED
        ver.archived_at = _now()
        ver.lock_version = int(ver.lock_version or 1) + 1
        self._session.add(ver)
        obj = await self._get_object(tenant_owner_id, ver.object_id)
        obj.status = KnowledgeGovernanceStatus.ARCHIVED
        obj.archived_at = _now()
        obj.updated_at = _now()
        self._session.add(obj)
        await self._audit(
            tenant_owner_id=tenant_owner_id,
            event_type="knowledge.archived",
            actor_user_id=actor_user_id,
            object_id=ver.object_id,
            version_id=version_id,
        )
        await self._session.commit()
        return {"version_id": str(version_id), "status": "archived"}

    async def list_objects(
        self, *, tenant_owner_id: UUID, status: str | None = None
    ) -> list[dict]:
        stmt = select(KnowledgeObjectTable).where(
            KnowledgeObjectTable.tenant_owner_id == tenant_owner_id
        )
        if status:
            stmt = stmt.where(KnowledgeObjectTable.status == status)
        result = await self._session.execute(stmt.order_by(KnowledgeObjectTable.updated_at.desc()))
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "code": r.code,
                "title": r.title,
                "domain": r.domain.value if hasattr(r.domain, "value") else str(r.domain),
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "current_version_id": str(r.current_version_id) if r.current_version_id else None,
                "visibility": r.visibility.value
                if hasattr(r.visibility, "value")
                else str(r.visibility),
            }
            for r in rows
        ]

    async def get_object_detail(
        self, *, tenant_owner_id: UUID, object_id: UUID
    ) -> dict:
        obj = await self._get_object(tenant_owner_id, object_id)
        vers = await self._session.execute(
            select(KnowledgeVersionTable).where(
                KnowledgeVersionTable.object_id == object_id,
                KnowledgeVersionTable.tenant_owner_id == tenant_owner_id,
            )
        )
        versions = vers.scalars().all()
        chunks = []
        if obj.current_version_id:
            ch = await self._session.execute(
                select(SemanticChunkTable).where(
                    SemanticChunkTable.version_id == obj.current_version_id
                )
            )
            chunks = [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "intent": c.intent,
                    "rule": c.rule[:500],
                    "source_location": c.source_location,
                }
                for c in ch.scalars().all()
            ]
        return {
            "id": str(obj.id),
            "code": obj.code,
            "title": obj.title,
            "domain": obj.domain.value if hasattr(obj.domain, "value") else str(obj.domain),
            "status": obj.status.value if hasattr(obj.status, "value") else str(obj.status),
            "current_version_id": str(obj.current_version_id) if obj.current_version_id else None,
            "versions": [
                {
                    "id": str(v.id),
                    "version": v.version,
                    "status": v.status.value if hasattr(v.status, "value") else str(v.status),
                    "freshness": v.freshness.value
                    if hasattr(v.freshness, "value")
                    else str(v.freshness),
                    "owner_user_id": str(v.owner_user_id) if v.owner_user_id else None,
                    "reviewer_user_id": str(v.reviewer_user_id)
                    if v.reviewer_user_id
                    else None,
                    "review_date": v.review_date.isoformat() if v.review_date else None,
                    "next_review_at": v.next_review_at.isoformat()
                    if v.next_review_at
                    else None,
                    "source_uri": v.source_uri,
                    "lock_version": v.lock_version,
                    "replacement_version_id": str(v.replacement_version_id)
                    if v.replacement_version_id
                    else None,
                }
                for v in versions
            ],
            "semantic_chunks": chunks,
        }

    async def scan_freshness(self, *, tenant_owner_id: UUID) -> list[dict]:
        stmt = select(KnowledgeVersionTable).where(
            KnowledgeVersionTable.tenant_owner_id == tenant_owner_id,
            KnowledgeVersionTable.status == KnowledgeGovernanceStatus.PUBLISHED,
        )
        result = await self._session.execute(stmt)
        out: list[dict] = []
        for ver in result.scalars().all():
            check = await self._persist_freshness(ver)
            # Due soon: 7–14 days
            due_task = False
            if ver.next_review_at:
                days = (ver.next_review_at - _now()).days
                if 0 <= days <= 14:
                    due_task = True
                    if days <= 14:
                        ver.freshness = (
                            KnowledgeFreshnessState.EXPIRED
                            if check.expired
                            else KnowledgeFreshnessState.DUE_FOR_REVIEW
                        )
                        self._session.add(ver)
            out.append(
                {
                    "version_id": str(ver.id),
                    "freshness": check.freshness.value,
                    "expired": check.expired,
                    "deprecated": check.deprecated,
                    "owner_review_task": due_task,
                    "safe_message": check.safe_message,
                }
            )
        await self._session.commit()
        return out

    async def _persist_freshness(self, ver: KnowledgeVersionTable):
        check = evaluate_knowledge_freshness(
            knowledge_id=ver.id,
            status=ver.status,
            review_date=ver.review_date,
            next_review=ver.next_review_at,
        )
        ver.freshness = check.freshness
        self._session.add(ver)
        self._session.add(
            KnowledgeFreshnessCheckTable(
                id=uuid4(),
                version_id=ver.id,
                object_id=ver.object_id,
                tenant_owner_id=ver.tenant_owner_id,
                freshness=check.freshness,
                expired=check.expired,
                deprecated=check.deprecated,
                review_date=ver.review_date,
                next_review_at=ver.next_review_at,
                safe_message=check.safe_message[:500],
                checked_at=_now(),
            )
        )
        return check

    async def _get_object(
        self, tenant_owner_id: UUID, object_id: UUID
    ) -> KnowledgeObjectTable:
        obj = await self._session.get(KnowledgeObjectTable, object_id)
        if obj is None or obj.tenant_owner_id != tenant_owner_id:
            raise LifecycleError("not_found", "Knowledge object not found")
        return obj

    async def _get_version(
        self, tenant_owner_id: UUID, version_id: UUID
    ) -> KnowledgeVersionTable:
        ver = await self._session.get(KnowledgeVersionTable, version_id)
        if ver is None or ver.tenant_owner_id != tenant_owner_id:
            raise LifecycleError("not_found", "Knowledge version not found")
        return ver

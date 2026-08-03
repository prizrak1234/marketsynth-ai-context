"""Deterministic knowledge retrieval adapter (Phase H2.4) — PostgreSQL filters, no embeddings."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_item import KnowledgeItemTable
from app.schemas.contracts import (
    KnowledgeItemStatus,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
    KnowledgeTenantScope,
    KnowledgeType,
    SpecialistSkillCode,
)

RETRIEVAL_POLICY_VERSION = "1.0"

_EXCLUDED_STATUSES = frozenset(
    {
        KnowledgeItemStatus.CANDIDATE,
        KnowledgeItemStatus.UNDER_REVIEW,
        KnowledgeItemStatus.REJECTED,
        KnowledgeItemStatus.SUPERSEDED,
        KnowledgeItemStatus.ARCHIVED,
    }
)

_SKILL_TAGS: dict[str, frozenset[str]] = {
    SpecialistSkillCode.CONTENT_TELEGRAM_POST.value: frozenset(
        {
            "telegram",
            "content",
            "methodology",
            "template",
            "quality",
            "brand",
            "factcheck",
            "content.telegram_post",
            "platform_fit",
            "brand_voice",
            "factuality",
            "assumptions",
            "constraints",
        }
    ),
}


def compute_snapshot_hash(
    *,
    skill_code: str,
    skill_version: str,
    capability_pack_version: str,
    retrieval_policy_version: str,
    locale: str,
    item_refs: list[dict],
) -> str:
    parts = [
        skill_code,
        skill_version,
        capability_pack_version,
        retrieval_policy_version,
        locale,
    ]
    for ref in sorted(
        item_refs,
        key=lambda r: (r.get("code", ""), r.get("version", ""), r.get("knowledge_item_id", "")),
    ):
        parts.append(
            "|".join(
                [
                    str(ref.get("knowledge_item_id", "")),
                    str(ref.get("code", "")),
                    str(ref.get("version", "")),
                    str(ref.get("content_hash", "")),
                ]
            )
        )
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _rank(row: KnowledgeItemTable) -> int:
    if row.knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY:
        return 0
    if row.tenant_scope == KnowledgeTenantScope.OWNER:
        return 2
    if row.tenant_scope == KnowledgeTenantScope.PROJECT:
        return 3
    if row.knowledge_type == KnowledgeType.EXAMPLE:
        return 4
    return 1


def _locale_ok(row: KnowledgeItemTable, locale: str, warnings: list[str]) -> bool:
    if row.locale == locale:
        return True
    # Language-neutral / EN constitutional may fall back for RU requests.
    if (
        row.knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY
        and row.locale in {"en", "und"}
        and locale != row.locale
    ):
        warnings.append(f"locale_fallback:{row.code}:{row.locale}->{locale}")
        return True
    # Content methodology EN is allowed when RU-specific method missing.
    if row.domain.value == "content" and row.locale == "en" and locale == "ru":
        warnings.append(f"content_locale_fallback:{row.code}")
        return True
    return False


def _scope_denied(
    row: KnowledgeItemTable,
    *,
    owner_id,
    project_id,
) -> bool:
    if row.tenant_scope == KnowledgeTenantScope.GLOBAL:
        return False
    if row.tenant_scope == KnowledgeTenantScope.OWNER:
        return row.owner_id is None or row.owner_id != owner_id
    if row.tenant_scope == KnowledgeTenantScope.PROJECT:
        if row.owner_id != owner_id or project_id is None or row.project_id != project_id:
            return True
        return False
    return True


def _is_expired(row: KnowledgeItemTable, now: datetime) -> bool:
    if row.valid_until is None:
        return False
    return row.valid_until <= now


def _relevance(
    row: KnowledgeItemTable,
    skill_code: str,
    skill_tags: frozenset[str],
) -> str | None:
    if row.knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY:
        return "constitutional_policy"
    tags = set(row.tags or [])
    overlap = tags.intersection(skill_tags)
    if skill_code in tags or skill_code.replace(".", "_") in tags:
        return f"skill_specific:{skill_code}"
    if overlap:
        return f"skill_tag_overlap:{','.join(sorted(overlap))}"
    if row.domain.value == "content" and skill_code.startswith("content."):
        return "skill_domain_content"
    if row.tenant_scope in {KnowledgeTenantScope.OWNER, KnowledgeTenantScope.PROJECT}:
        return f"scoped_{row.tenant_scope.value}"
    if row.knowledge_type == KnowledgeType.EXAMPLE:
        return "approved_example"
    return None


class KnowledgeRetrievalAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        request: KnowledgeRetrievalRequest,
        *,
        include_content: bool = False,
    ) -> KnowledgeRetrievalResult:
        skill_code = (
            request.skill_code
            if isinstance(request.skill_code, str)
            else str(request.skill_code)
        )
        skill_tags = _SKILL_TAGS.get(skill_code, frozenset({"content"}))
        now = utc_now()
        warnings: list[str] = []
        excluded = 0

        stmt = select(KnowledgeItemTable)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        hits: list[tuple[int, KnowledgeRetrievalItem]] = []
        for row in rows:
            if row.status in _EXCLUDED_STATUSES:
                excluded += 1
                continue
            if row.status != KnowledgeItemStatus.APPROVED:
                excluded += 1
                continue
            if row.knowledge_type in {
                KnowledgeType.OBSOLETE,
                KnowledgeType.FORBIDDEN,
                KnowledgeType.HISTORICAL_RECORD,
            }:
                excluded += 1
                continue
            if _is_expired(row, now):
                excluded += 1
                continue
            if _scope_denied(
                row,
                owner_id=request.owner_id,
                project_id=request.project_id,
            ):
                excluded += 1
                continue
            if not _locale_ok(row, request.locale, warnings):
                excluded += 1
                continue
            if request.specialist_role and row.specialist_roles:
                roles = set(row.specialist_roles)
                if (
                    "*" not in roles
                    and request.specialist_role not in roles
                    and row.knowledge_type != KnowledgeType.CONSTITUTIONAL_POLICY
                ):
                    excluded += 1
                    continue
            reason = _relevance(row, skill_code, skill_tags)
            if reason is None:
                excluded += 1
                continue
            hits.append(
                (
                    _rank(row),
                    KnowledgeRetrievalItem(
                        knowledge_item_id=row.id,
                        code=row.code,
                        version=row.version,
                        title=row.title,
                        knowledge_type=row.knowledge_type,
                        source_uri=row.source_uri,
                        authority=row.authority,
                        tenant_scope=row.tenant_scope,
                        owner_id=row.owner_id,
                        project_id=row.project_id,
                        citation_required=row.citation_required,
                        relevance_reason=reason,
                        content_hash=row.content_hash,
                        locale=row.locale,
                        include_content=include_content,
                        content=row.content if include_content else None,
                    ),
                )
            )

        hits.sort(key=lambda pair: (pair[0], pair[1].code, pair[1].version))
        items = [item for _, item in hits[: request.limit]]
        refs = [
            {
                "knowledge_item_id": str(item.knowledge_item_id),
                "code": item.code,
                "version": item.version,
                "content_hash": item.content_hash,
            }
            for item in items
        ]
        snap = compute_snapshot_hash(
            skill_code=skill_code,
            skill_version=request.skill_version,
            capability_pack_version="pending",
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            locale=request.locale,
            item_refs=refs,
        )
        return KnowledgeRetrievalResult(
            items=items,
            snapshot_hash=snap,
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            excluded_count=excluded,
            warnings=warnings,
        )

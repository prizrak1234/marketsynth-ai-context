"""Knowledge admission policy — only approved items may serve specialists."""

from __future__ import annotations

from app.schemas.contracts import KnowledgeItem, KnowledgeItemStatus, KnowledgeType

REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "knowledge_type",
    "domain",
    "specialist_roles",
    "source_uri",
    "source_hash",
    "version",
    "status",
    "authority",
    "tenant_scope",
    "project_id",
    "locale",
    "valid_from",
    "valid_until",
    "supersedes_id",
    "tags",
    "citation_required",
    "created_at",
    "reviewed_at",
    "reviewed_by",
)

KNOWLEDGE_ADMISSION_RULES: dict[str, str] = {
    "production_requires_approved": (
        "Only status=approved knowledge may be used in production specialist work."
    ),
    "no_bulk_docs_index": (
        "Recursive indexing of /docs, phase reports, audits, mocks, and secrets is forbidden."
    ),
    "allowlist_only": "Candidates must come from explicit source allowlists.",
    "no_forbidden_types": (
        "knowledge_type obsolete/forbidden never admit; historical_record is not operational."
    ),
    "tenant_isolation": "Owner/project knowledge never crosses tenant boundaries.",
    "citations": "Research/strategy claims require citation_required=true when factual.",
    "no_secrets": "Raw credentials, private keys, and chain-of-thought are never admitted.",
    "review_required": "candidate → under_review → approved|rejected; no silent promote.",
}


def required_metadata_fields() -> tuple[str, ...]:
    return REQUIRED_METADATA_FIELDS


def can_admit_to_production(item: KnowledgeItem) -> bool:
    if item.status != KnowledgeItemStatus.APPROVED:
        return False
    if item.knowledge_type in {
        KnowledgeType.OBSOLETE,
        KnowledgeType.FORBIDDEN,
        KnowledgeType.HISTORICAL_RECORD,
    }:
        return False
    if item.valid_until is not None and item.valid_until <= item.valid_from:
        return False
    return True


def transition_on_approve(item: KnowledgeItem) -> KnowledgeItemStatus | None:
    if item.status in {
        KnowledgeItemStatus.CANDIDATE,
        KnowledgeItemStatus.UNDER_REVIEW,
    }:
        if item.knowledge_type in {
            KnowledgeType.OBSOLETE,
            KnowledgeType.FORBIDDEN,
        }:
            return None
        return KnowledgeItemStatus.APPROVED
    return None


def transition_on_reject(item: KnowledgeItem) -> KnowledgeItemStatus | None:
    if item.status in {
        KnowledgeItemStatus.CANDIDATE,
        KnowledgeItemStatus.UNDER_REVIEW,
        KnowledgeItemStatus.APPROVED,
    }:
        return KnowledgeItemStatus.REJECTED
    return None

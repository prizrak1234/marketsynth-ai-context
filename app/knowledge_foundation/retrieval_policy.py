"""Deterministic knowledge retrieval policy — no vector similarity as confidence."""

from __future__ import annotations

from uuid import UUID

from app.knowledge_foundation.admission import can_admit_to_production
from app.knowledge_foundation.inventory import list_inventory
from app.knowledge_foundation.scopes import is_cross_tenant_denied
from app.schemas.contracts import (
    KnowledgeItem,
    KnowledgeItemStatus,
    KnowledgeRetrievalHit,
    KnowledgeType,
    SpecialistSkillCode,
)

RETRIEVAL_ORDER: tuple[str, ...] = (
    "constitutional_policy",
    "skill_specific_approved",
    "owner_knowledge",
    "project_knowledge",
    "approved_examples",
)

_EXCLUDED_FROM_RETRIEVAL: frozenset[KnowledgeItemStatus] = frozenset(
    {
        KnowledgeItemStatus.CANDIDATE,
        KnowledgeItemStatus.UNDER_REVIEW,
        KnowledgeItemStatus.REJECTED,
        KnowledgeItemStatus.SUPERSEDED,
        KnowledgeItemStatus.ARCHIVED,
    }
)

_SKILL_SCOPE_TAGS: dict[SpecialistSkillCode, frozenset[str]] = {
    SpecialistSkillCode.CONTENT_TELEGRAM_POST: frozenset(
        {"telegram", "content", "brand_voice", "platform_fit"}
    ),
    SpecialistSkillCode.CONTENT_SOCIAL_POST: frozenset({"social", "content", "brand_voice"}),
    SpecialistSkillCode.CONTENT_CONTENT_PLAN: frozenset({"content_plan", "content", "template"}),
    SpecialistSkillCode.CONTENT_YOUTUBE_SCRIPT: frozenset({"youtube", "content"}),
    SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW: frozenset(
        {"jtbd", "segmentation", "research", "citations"}
    ),
    SpecialistSkillCode.RESEARCH_COMPETITOR_ANALYSIS: frozenset(
        {"competitors", "research", "citations"}
    ),
    SpecialistSkillCode.RESEARCH_AUDIENCE_SEGMENTATION: frozenset(
        {"segmentation", "audience", "research"}
    ),
    SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC: frozenset(
        {"telegram_bot", "spec_only", "template"}
    ),
    SpecialistSkillCode.PROGRAMMER_WEBSITE_SPEC: frozenset({"website", "spec_only"}),
    SpecialistSkillCode.PROGRAMMER_AUTOMATION_SPEC: frozenset({"automation", "spec_only"}),
    SpecialistSkillCode.STRATEGY_POSITIONING: frozenset({"positioning", "strategy"}),
    SpecialistSkillCode.STRATEGY_OFFER_DESIGN: frozenset({"offer", "strategy"}),
    SpecialistSkillCode.STRATEGY_CHANNEL_SELECTION: frozenset({"channel", "strategy"}),
}


def _rank_bucket(item: KnowledgeItem) -> int:
    if item.knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY:
        return 0
    if item.knowledge_type in {
        KnowledgeType.DOMAIN_METHODOLOGY,
        KnowledgeType.OUTPUT_TEMPLATE,
        KnowledgeType.QUALITY_STANDARD,
        KnowledgeType.WORKFLOW_INSTRUCTION,
        KnowledgeType.VERIFIED_FACT,
    }:
        return 1
    if item.tenant_scope.value == "owner":
        return 2
    if item.tenant_scope.value == "project" or item.knowledge_type == KnowledgeType.PROJECT_KNOWLEDGE:
        return 3
    if item.knowledge_type == KnowledgeType.EXAMPLE:
        return 4
    return 9


def retrieve_for_skill(
    skill_code: SpecialistSkillCode,
    *,
    requester_owner_id: UUID | None,
    requester_project_id: UUID | None = None,
    specialist_role: str | None = None,
) -> list[KnowledgeRetrievalHit]:
    """Return approved, in-scope knowledge in deterministic order.

    Does not create embeddings. Does not expose similarity scores as confidence.
    """
    tags = _SKILL_SCOPE_TAGS.get(skill_code, frozenset())
    hits: list[tuple[int, KnowledgeRetrievalHit]] = []
    for item in list_inventory():
        if item.status in _EXCLUDED_FROM_RETRIEVAL:
            continue
        if item.knowledge_type in {
            KnowledgeType.OBSOLETE,
            KnowledgeType.FORBIDDEN,
            KnowledgeType.HISTORICAL_RECORD,
        }:
            continue
        if not can_admit_to_production(item):
            continue
        if is_cross_tenant_denied(
            item,
            requester_owner_id=requester_owner_id,
            requester_project_id=requester_project_id,
        ):
            continue
        if specialist_role and item.specialist_roles:
            if "*" not in item.specialist_roles and specialist_role not in item.specialist_roles:
                # Constitutional still applies to all roles.
                if item.knowledge_type != KnowledgeType.CONSTITUTIONAL_POLICY:
                    continue
        reason = _relevance_reason(item, tags)
        if reason is None and item.knowledge_type != KnowledgeType.CONSTITUTIONAL_POLICY:
            continue
        hits.append(
            (
                _rank_bucket(item),
                KnowledgeRetrievalHit(
                    knowledge_id=item.id,
                    version=item.version,
                    source_uri=item.source_uri,
                    authority=item.authority,
                    tenant_scope=item.tenant_scope,
                    owner_id=item.owner_id,
                    project_id=item.project_id,
                    relevance_reason=reason
                    or "constitutional_policy_applies_to_all_skills",
                    citation_required=item.citation_required,
                    knowledge_type=item.knowledge_type,
                ),
            )
        )
    hits.sort(key=lambda pair: (pair[0], pair[1].knowledge_id))
    return [hit for _, hit in hits]


def _relevance_reason(item: KnowledgeItem, skill_tags: frozenset[str]) -> str | None:
    if item.knowledge_type == KnowledgeType.CONSTITUTIONAL_POLICY:
        return "constitutional_policy"
    overlap = skill_tags.intersection(item.tags)
    if overlap:
        return f"skill_tag_overlap:{','.join(sorted(overlap))}"
    if item.domain.value in {"content", "research", "programmer", "strategy", "marketing"}:
        # Domain-level match when tags empty for templates.
        if item.knowledge_type in {
            KnowledgeType.DOMAIN_METHODOLOGY,
            KnowledgeType.OUTPUT_TEMPLATE,
            KnowledgeType.QUALITY_STANDARD,
        }:
            return f"domain_methodology:{item.domain.value}"
    if item.tenant_scope.value in {"owner", "project"}:
        return f"scoped_{item.tenant_scope.value}_knowledge"
    if item.knowledge_type == KnowledgeType.EXAMPLE:
        return "approved_example_reference"
    return None

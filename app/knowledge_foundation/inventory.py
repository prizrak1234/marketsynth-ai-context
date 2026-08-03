"""Curated Knowledge Inventory — classification only; no bulk ingest."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.knowledge_foundation.allowlists import is_path_allowlisted, is_path_blocked
from app.knowledge_foundation.review_store import apply_review_overlay, get_overlay
from app.schemas.contracts import (
    KnowledgeAuthority,
    KnowledgeDomain,
    KnowledgeInventoryFilter,
    KnowledgeItem,
    KnowledgeItemStatus,
    KnowledgeTenantScope,
    KnowledgeType,
)

_UTC = timezone.utc


def _ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=_UTC)


def _build_seed_inventory() -> list[KnowledgeItem]:
    """Explicit curated entries — never derived from recursive directory walks."""
    return [
        KnowledgeItem(
            id="kn.const.marketsynth_invariants",
            title="Marketsynth constitutional invariants",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONSTITUTIONAL,
            specialist_roles=["*"],
            source_uri="docs/AGENT_OS_ARCHITECTURE.md",
            source_hash="allowlist:agent_os_architecture",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["no_fake_facts", "insufficient_data", "tenant_isolation", "approval"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
            notes="Core product constraints for every specialist.",
        ),
        KnowledgeItem(
            id="kn.const.insufficient_data",
            title="INSUFFICIENT_DATA and no-guesswork policy",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONSTITUTIONAL,
            specialist_roles=["*"],
            source_uri="docs/CURSOR_OPERATING_RULES.md",
            source_hash="allowlist:cursor_operating_rules",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["insufficient_data", "provenance"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.const.ru_invariants",
            title="Конституционные правила Marketsynth (RU metadata)",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONSTITUTIONAL,
            specialist_roles=["*"],
            source_uri="docs/PROJECT_VISION.md",
            source_hash="allowlist:project_vision",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="ru",
            valid_from=_ts(2026, 7, 1),
            tags=["ru", "constitutional"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.meth.research_overview",
            title="Marketing research methodology",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.RESEARCH,
            specialist_roles=["researcher"],
            source_uri="docs/MARKETING_FRAMEWORKS_CONTEXT.md",
            source_hash="allowlist:marketing_frameworks",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.DOMAIN,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["jtbd", "segmentation", "competitors"],
            citation_required=True,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.meth.content",
            title="Content production methodology",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.CONTENT,
            specialist_roles=["content_specialist", "content_planner"],
            source_uri="skills/content-production",
            source_hash="allowlist:content_production_skill",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.DOMAIN,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["telegram", "social", "content_plan", "youtube"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.meth.programmer_spec",
            title="Programmer specification methodology",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.PROGRAMMER,
            specialist_roles=["programmer"],
            source_uri="docs/AGENT_OS_ARCHITECTURE.md",
            source_hash="allowlist:programmer_spec_method",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.DOMAIN,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["telegram_bot", "website", "automation", "spec_only"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.tmpl.research_report",
            title="Research report output template",
            knowledge_type=KnowledgeType.OUTPUT_TEMPLATE,
            domain=KnowledgeDomain.RESEARCH,
            specialist_roles=["researcher"],
            source_uri="skills/segment-research",
            source_hash="allowlist:research_report_template",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.PRODUCT,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["template", "citations"],
            citation_required=True,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.tmpl.content_plan",
            title="Content plan output template",
            knowledge_type=KnowledgeType.OUTPUT_TEMPLATE,
            domain=KnowledgeDomain.CONTENT,
            specialist_roles=["content_planner", "content_specialist"],
            source_uri="skills/content-production",
            source_hash="allowlist:content_plan_template",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.PRODUCT,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["template", "content_plan"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.tmpl.telegram_bot_spec",
            title="Telegram bot specification template",
            knowledge_type=KnowledgeType.OUTPUT_TEMPLATE,
            domain=KnowledgeDomain.PROGRAMMER,
            specialist_roles=["programmer"],
            source_uri="docs/AGENT_OS_ARCHITECTURE.md",
            source_hash="allowlist:telegram_bot_spec_template",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.PRODUCT,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["template", "telegram_bot"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.qual.content_gates",
            title="Content quality gates",
            knowledge_type=KnowledgeType.QUALITY_STANDARD,
            domain=KnowledgeDomain.CONTENT,
            specialist_roles=["content_specialist", "content_planner"],
            source_uri="skills/supervisor-quality",
            source_hash="allowlist:content_quality",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.PRODUCT,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 7, 1),
            tags=["no_fake_facts", "platform_fit", "brand_voice"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.cand.wordstat_corpus",
            title="Imported Wordstat corpus (unreviewed)",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.MARKETING,
            specialist_roles=["researcher"],
            source_uri="knowledge/wordstat",
            source_hash=None,
            version="0.1",
            status=KnowledgeItemStatus.CANDIDATE,
            authority=KnowledgeAuthority.DOMAIN,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="ru",
            valid_from=_ts(2026, 6, 4),
            tags=["imported", "needs_atomic_split"],
            citation_required=True,
            migration_action="include_after_review",
            notes="Directory-level candidate only — not ingested.",
        ),
        KnowledgeItem(
            id="kn.cand.misc_n8n_examples",
            title="Imported misc automation examples",
            knowledge_type=KnowledgeType.EXAMPLE,
            domain=KnowledgeDomain.MIXED,
            specialist_roles=[],
            source_uri="knowledge/misc",
            source_hash=None,
            version="0.1",
            status=KnowledgeItemStatus.CANDIDATE,
            authority=KnowledgeAuthority.EXAMPLE,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="ru",
            valid_from=_ts(2026, 6, 4),
            tags=["example", "not_fact"],
            citation_required=False,
            migration_action="split_into_atomic_knowledge_items",
        ),
        KnowledgeItem(
            id="kn.hist.phase_ai_39_audit",
            title="Phase AI.39 marketing pipeline readiness audit",
            knowledge_type=KnowledgeType.HISTORICAL_RECORD,
            domain=KnowledgeDomain.OPERATIONS,
            specialist_roles=[],
            source_uri="docs/phase_ai_39_marketing_pipeline_readiness_audit.md",
            source_hash=None,
            version="1.0",
            status=KnowledgeItemStatus.ARCHIVED,
            authority=KnowledgeAuthority.HISTORICAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 1, 1),
            tags=["phase_report", "audit"],
            citation_required=False,
            migration_action="keep_as_historical_record",
        ),
        KnowledgeItem(
            id="kn.obs.legacy_botfazer_readme",
            title="Obsolete BotFazer README instructions",
            knowledge_type=KnowledgeType.OBSOLETE,
            domain=KnowledgeDomain.OPERATIONS,
            specialist_roles=[],
            source_uri="docs/obsolete_botfazer_readme.md",
            source_hash=None,
            version="0.0",
            status=KnowledgeItemStatus.REJECTED,
            authority=KnowledgeAuthority.HISTORICAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2025, 1, 1),
            tags=["botfazer", "obsolete"],
            citation_required=False,
            migration_action="obsolete",
        ),
        KnowledgeItem(
            id="kn.forb.workflows_raw",
            title="Raw n8n/Make workflow dumps",
            knowledge_type=KnowledgeType.FORBIDDEN,
            domain=KnowledgeDomain.OPERATIONS,
            specialist_roles=[],
            source_uri="workflows/raw/",
            source_hash=None,
            version="0.0",
            status=KnowledgeItemStatus.REJECTED,
            authority=KnowledgeAuthority.HISTORICAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 6, 4),
            tags=["forbidden", "no_auto_exec"],
            citation_required=False,
            migration_action="exclude",
        ),
        KnowledgeItem(
            id="kn.forb.secrets_env",
            title="Environment secrets",
            knowledge_type=KnowledgeType.FORBIDDEN,
            domain=KnowledgeDomain.OPERATIONS,
            specialist_roles=[],
            source_uri=".env",
            source_hash=None,
            version="0.0",
            status=KnowledgeItemStatus.REJECTED,
            authority=KnowledgeAuthority.HISTORICAL,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 1, 1),
            tags=["secrets", "forbidden"],
            citation_required=False,
            migration_action="exclude",
        ),
        KnowledgeItem(
            id="kn.ex.owner_brand_demo",
            title="Example owner brand brief (demo scope)",
            knowledge_type=KnowledgeType.EXAMPLE,
            domain=KnowledgeDomain.CONTENT,
            specialist_roles=["content_specialist"],
            source_uri="examples/owner_brand_brief.md",
            source_hash="example:owner_brand",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.EXAMPLE,
            tenant_scope=KnowledgeTenantScope.OWNER,
            owner_id=UUID("00000000-0000-4000-8000-000000000001"),
            locale="ru",
            valid_from=_ts(2026, 7, 1),
            tags=["example", "brand"],
            citation_required=False,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include_after_review",
        ),
        KnowledgeItem(
            id="kn.proj.demo_brief",
            title="Demo project brief knowledge",
            knowledge_type=KnowledgeType.PROJECT_KNOWLEDGE,
            domain=KnowledgeDomain.PRODUCT,
            specialist_roles=["researcher", "strategist", "content_specialist"],
            source_uri="project://demo/brief",
            source_hash="project:demo_brief",
            version="1.0",
            status=KnowledgeItemStatus.APPROVED,
            authority=KnowledgeAuthority.PROJECT,
            tenant_scope=KnowledgeTenantScope.PROJECT,
            owner_id=UUID("00000000-0000-4000-8000-000000000001"),
            project_id=UUID("00000000-0000-4000-8000-0000000000aa"),
            locale="ru",
            valid_from=_ts(2026, 7, 1),
            tags=["project", "brief"],
            citation_required=True,
            reviewed_at=_ts(2026, 7, 16),
            reviewed_by="h2.1_foundation",
            migration_action="include",
        ),
        KnowledgeItem(
            id="kn.super.research_v1",
            title="Superseded research methodology v1",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.RESEARCH,
            specialist_roles=["researcher"],
            source_uri="docs/MARKETING_FRAMEWORKS_CONTEXT.md",
            source_hash="old:research_v1",
            version="0.9",
            status=KnowledgeItemStatus.SUPERSEDED,
            authority=KnowledgeAuthority.DOMAIN,
            tenant_scope=KnowledgeTenantScope.GLOBAL,
            locale="en",
            valid_from=_ts(2026, 1, 1),
            valid_until=_ts(2026, 7, 1),
            tags=["superseded"],
            citation_required=True,
            migration_action="keep_as_historical_record",
            notes="Superseded by kn.meth.research_overview",
        ),
    ]


_SEED: list[KnowledgeItem] | None = None


def _seed() -> list[KnowledgeItem]:
    global _SEED
    if _SEED is None:
        _SEED = _build_seed_inventory()
        for item in _SEED:
            if item.source_uri and is_path_blocked(item.source_uri):
                # Blocked paths may only appear as forbidden/obsolete/historical markers.
                assert item.knowledge_type in {
                    KnowledgeType.FORBIDDEN,
                    KnowledgeType.OBSOLETE,
                    KnowledgeType.HISTORICAL_RECORD,
                }
            elif item.migration_action == "include":
                assert is_path_allowlisted(item.source_uri) or item.source_uri.startswith(
                    ("project://", "examples/")
                )
    return _SEED


def list_inventory(*, include_overlay: bool = True) -> list[KnowledgeItem]:
    items = [item.model_copy(deep=True) for item in _seed()]
    if include_overlay:
        return [apply_review_overlay(item) for item in items]
    return items


def get_inventory_item(item_id: str) -> KnowledgeItem | None:
    for item in list_inventory():
        if item.id == item_id:
            return item
    return None


def filter_inventory(filters: KnowledgeInventoryFilter | None = None) -> list[KnowledgeItem]:
    items = list_inventory()
    if filters is None:
        return items
    out: list[KnowledgeItem] = []
    for item in items:
        if filters.knowledge_type and item.knowledge_type != filters.knowledge_type:
            continue
        if filters.domain and item.domain != filters.domain:
            continue
        if filters.status and item.status != filters.status:
            continue
        if filters.locale and item.locale != filters.locale:
            continue
        if filters.specialist_role:
            roles = item.specialist_roles
            if "*" not in roles and filters.specialist_role not in roles:
                continue
        out.append(item)
    return out


def reset_inventory_cache_for_tests() -> None:
    """Test helper — clears seed cache and review overlay."""
    global _SEED
    _SEED = None
    get_overlay().clear()

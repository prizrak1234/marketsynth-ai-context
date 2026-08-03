"""Migration manifest for collected corpus — classify, do not auto-migrate."""

from __future__ import annotations

from typing import TypedDict


class MigrationManifestEntry(TypedDict):
    source: str
    action: str
    knowledge_type_hint: str
    notes: str


MIGRATION_MANIFEST: list[MigrationManifestEntry] = [
    {
        "source": "docs/PROJECT_VISION.md",
        "action": "include",
        "knowledge_type_hint": "constitutional_policy",
        "notes": "Product constitution — first approved pack.",
    },
    {
        "source": "docs/AGENT_OS_ARCHITECTURE.md",
        "action": "include",
        "knowledge_type_hint": "constitutional_policy",
        "notes": "Agent OS invariants; split programmer methodology separately.",
    },
    {
        "source": "docs/MARKETING_FRAMEWORKS_CONTEXT.md",
        "action": "include",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Research/strategy frameworks.",
    },
    {
        "source": "docs/MARKETING_AGENT_TARGET_MODEL.md",
        "action": "include_after_review",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Business-first outputs; review before operational use.",
    },
    {
        "source": "docs/KNOWLEDGE_ARCHITECTURE.md",
        "action": "include_after_review",
        "knowledge_type_hint": "operational_document",
        "notes": "Architecture map — not specialist runtime truth.",
    },
    {
        "source": "skills/content-production",
        "action": "include",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Content methodology + templates.",
    },
    {
        "source": "skills/segment-research",
        "action": "include",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Research methodology pack.",
    },
    {
        "source": "skills/offer-packaging",
        "action": "include_after_review",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Strategy offer design support.",
    },
    {
        "source": "skills/supervisor-quality",
        "action": "include",
        "knowledge_type_hint": "quality_standard",
        "notes": "Quality gates for drafts.",
    },
    {
        "source": "knowledge/manuals",
        "action": "split_into_atomic_knowledge_items",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Manual mix — atomicize before approve.",
    },
    {
        "source": "knowledge/positioning",
        "action": "include_after_review",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Strategy positioning candidates.",
    },
    {
        "source": "knowledge/audience",
        "action": "include_after_review",
        "knowledge_type_hint": "domain_methodology",
        "notes": "Audience segmentation candidates.",
    },
    {
        "source": "knowledge/wordstat",
        "action": "include_after_review",
        "knowledge_type_hint": "example",
        "notes": "Imported workflows — examples, not facts.",
    },
    {
        "source": "knowledge/misc",
        "action": "exclude",
        "knowledge_type_hint": "example",
        "notes": "Mostly unrelated automation dumps.",
    },
    {
        "source": "knowledge/prompts",
        "action": "exclude",
        "knowledge_type_hint": "forbidden",
        "notes": "Raw prompts are not KnowledgeItem content for specialists.",
    },
    {
        "source": "workflows/raw/",
        "action": "exclude",
        "knowledge_type_hint": "forbidden",
        "notes": "No auto-execution; archive only.",
    },
    {
        "source": "knowledge_import/",
        "action": "keep_as_historical_record",
        "knowledge_type_hint": "historical_record",
        "notes": "Staging mirror — not production knowledge.",
    },
    {
        "source": "docs/phase_ai_*",
        "action": "keep_as_historical_record",
        "knowledge_type_hint": "historical_record",
        "notes": "Phase reports/audits — never operational truth.",
    },
    {
        "source": "docs/*audit*.md",
        "action": "keep_as_historical_record",
        "knowledge_type_hint": "historical_record",
        "notes": "Unreviewed audits excluded from retrieval.",
    },
    {
        "source": "tests/",
        "action": "exclude",
        "knowledge_type_hint": "forbidden",
        "notes": "Test fixtures and outputs.",
    },
    {
        "source": ".env / secrets",
        "action": "exclude",
        "knowledge_type_hint": "forbidden",
        "notes": "Never index credentials.",
    },
    {
        "source": "obsolete BotFazer brand docs",
        "action": "obsolete",
        "knowledge_type_hint": "obsolete",
        "notes": "Legacy naming/instructions conflict with Marketsynth.",
    },
]

FIRST_APPROVED_PACK_IDS: tuple[str, ...] = (
    "kn.const.marketsynth_invariants",
    "kn.const.insufficient_data",
    "kn.const.ru_invariants",
    "kn.meth.research_overview",
    "kn.meth.content",
    "kn.meth.programmer_spec",
    "kn.tmpl.research_report",
    "kn.tmpl.content_plan",
    "kn.tmpl.telegram_bot_spec",
    "kn.qual.content_gates",
)


def list_manifest() -> list[MigrationManifestEntry]:
    return list(MIGRATION_MANIFEST)


def actions_for_source(source: str) -> list[str]:
    return [entry["action"] for entry in MIGRATION_MANIFEST if entry["source"] == source]

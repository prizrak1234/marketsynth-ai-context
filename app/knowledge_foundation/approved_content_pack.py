"""Approved content knowledge pack A–D — curated bodies for ingestion (Phase H2.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.contracts import (
    KnowledgeAuthority,
    KnowledgeContentFormat,
    KnowledgeDomain,
    KnowledgeItemStatus,
    KnowledgeTenantScope,
    KnowledgeType,
)


@dataclass(frozen=True, slots=True)
class PackSeed:
    code: str
    title: str
    knowledge_type: KnowledgeType
    domain: KnowledgeDomain
    content: str
    source_uri: str
    source_hash: str
    version: str
    authority: KnowledgeAuthority
    locale: str
    tags: tuple[str, ...]
    specialist_roles: tuple[str, ...]
    citation_required: bool
    pack: str
    content_format: KnowledgeContentFormat = KnowledgeContentFormat.MARKDOWN
    tenant_scope: KnowledgeTenantScope = KnowledgeTenantScope.GLOBAL
    metadata: dict[str, Any] | None = None


CONSTITUTIONAL_EN = """# Marketsynth constitutional invariants

1. Never present guesses or invented details as verified facts.
2. When evidence is missing, state INSUFFICIENT_DATA explicitly.
3. Never retrieve or mix knowledge across tenants (owners).
4. Never run automatic specialist execution, AgentRun, or publication without explicit owner action.
5. Respect approval boundaries: drafts require owner review before finalization.
6. Never place secrets, credentials, or API keys in prompts or outputs.
7. Never expose hidden chain-of-thought; keep internal reasoning private.
8. Preserve Source/Evidence lineage for material claims.
"""

CONSTITUTIONAL_RU = """# Конституционные правила Marketsynth

1. Не выдавать догадки и выдуманные детали за проверенные факты.
2. При нехватке данных явно указывать INSUFFICIENT_DATA.
3. Запрещён cross-tenant retrieval знаний.
4. Запрещён автоматический запуск специалистов, AgentRun и публикаций без явного действия владельца.
5. Черновики требуют review владельца до финализации.
6. Секреты и credentials не попадают в промпты и ответы.
7. Скрытый chain-of-thought не раскрывается пользователю.
8. Для существенных утверждений сохраняется lineage Source/Evidence.
"""

CONTENT_METHOD_TELEGRAM = """# Content methodology — Telegram post

## Structure
- Hook (first 1–2 lines) that earns attention without clickbait fraud.
- Body aligned to audience and objective.
- Clear CTA when objective requires action.

## Rules
- Audience alignment: vocabulary and pains must match the named audience.
- Objective/CTA alignment: CTA must serve the stated objective.
- Tone consistency across the draft.
- Platform fit: Telegram-readable length, line breaks, no Instagram-only formatting assumptions.
- No unsupported factual claims: if a fact is not verified, omit, mark as assumption, or request data.
- Brand constraints override stylistic preferences when provided.
"""

TELEGRAM_OUTPUT_TEMPLATE = """# Output template — content.telegram_post

```json
{
  "hook": "string",
  "main_text": "string",
  "cta": "string|null",
  "variants": ["optional alternative drafts"],
  "assumptions": ["explicit non-verified assumptions"],
  "factual_claim_flags": [
    {"claim": "string", "status": "verified|assumption|insufficient_data"}
  ],
  "review_checklist": [
    "platform_fit",
    "no_fake_facts",
    "brand_voice",
    "cta_alignment"
  ]
}
```

Visible citations are not required for pure copy methodology, but factual external claims must be flagged.
"""

CONTENT_QUALITY = """# Quality standard — content drafts

- Clarity: one idea per paragraph where possible.
- Relevance: every sentence serves topic, audience, or objective.
- Specificity: prefer concrete over vague marketing filler.
- No hallucinated facts.
- Brand voice respect.
- Language quality (ru/en as requested).
- Prohibited: hate, illegal instructions, secrets, fabricated statistics.
"""

BRAND_COPY_CONSTRAINTS = """# Brand / copy constraints (default product pack)

- Do not invent awards, clients, metrics, or partnerships.
- Prefer plain language over hype.
- If brand constraints are provided by the owner, they take precedence.
- Factuality mode:
  - strict: no unverified claims;
  - balanced: mark assumptions;
  - creative: creative phrasing allowed but still no fabricated facts.
"""

FACTCHECK_ASSUMPTIONS = """# Fact-checking and assumptions policy (content)

1. Methodology guidance may stay internal (no visible citation required).
2. External factual claims require Source/Evidence or must be:
   - removed,
   - marked as assumption,
   - or deferred with a data request.
3. Never convert assumptions into facts silently.
4. INSUFFICIENT_DATA is a valid specialist outcome for factual gaps.
"""


def approved_content_pack_seeds() -> list[PackSeed]:
    """Minimal Pack A–D for content.telegram_post — no research/strategy bulk."""
    return [
        PackSeed(
            code="ms.const.invariants.en",
            title="Marketsynth constitutional invariants (EN)",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONSTITUTIONAL,
            content=CONSTITUTIONAL_EN,
            source_uri="canonical://marketsynth/constitutional/invariants.en",
            source_hash="sha256:pack_a_const_en_v1",
            version="1.0",
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            locale="en",
            tags=("constitutional", "no_fake_facts", "insufficient_data", "tenant_isolation"),
            specialist_roles=("*",),
            citation_required=False,
            pack="A",
        ),
        PackSeed(
            code="ms.const.invariants.ru",
            title="Конституционные правила Marketsynth (RU)",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONSTITUTIONAL,
            content=CONSTITUTIONAL_RU,
            source_uri="canonical://marketsynth/constitutional/invariants.ru",
            source_hash="sha256:pack_a_const_ru_v1",
            version="1.0",
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            locale="ru",
            tags=("constitutional", "no_fake_facts", "insufficient_data", "ru"),
            specialist_roles=("*",),
            citation_required=False,
            pack="A",
        ),
        PackSeed(
            code="ms.content.telegram_methodology",
            title="Telegram post content methodology",
            knowledge_type=KnowledgeType.DOMAIN_METHODOLOGY,
            domain=KnowledgeDomain.CONTENT,
            content=CONTENT_METHOD_TELEGRAM,
            source_uri="canonical://marketsynth/content/telegram_methodology",
            source_hash="sha256:pack_b_telegram_method_v1",
            version="1.0",
            authority=KnowledgeAuthority.DOMAIN,
            locale="en",
            tags=("content", "telegram", "methodology", "platform_fit", "brand_voice"),
            specialist_roles=("content_specialist",),
            citation_required=False,
            pack="B",
        ),
        PackSeed(
            code="ms.content.telegram_output_template",
            title="content.telegram_post output template",
            knowledge_type=KnowledgeType.OUTPUT_TEMPLATE,
            domain=KnowledgeDomain.CONTENT,
            content=TELEGRAM_OUTPUT_TEMPLATE,
            source_uri="canonical://marketsynth/content/telegram_output_template",
            source_hash="sha256:pack_c_telegram_template_v1",
            version="1.0",
            authority=KnowledgeAuthority.PRODUCT,
            locale="en",
            tags=("content", "telegram", "template", "content.telegram_post"),
            specialist_roles=("content_specialist",),
            citation_required=False,
            pack="C",
        ),
        PackSeed(
            code="ms.content.quality_standard",
            title="Content quality standard",
            knowledge_type=KnowledgeType.QUALITY_STANDARD,
            domain=KnowledgeDomain.CONTENT,
            content=CONTENT_QUALITY,
            source_uri="canonical://marketsynth/content/quality_standard",
            source_hash="sha256:pack_d_quality_v1",
            version="1.0",
            authority=KnowledgeAuthority.PRODUCT,
            locale="en",
            tags=("content", "quality", "no_fake_facts", "brand_voice"),
            specialist_roles=("content_specialist", "content_planner"),
            citation_required=False,
            pack="D",
        ),
        PackSeed(
            code="ms.content.brand_copy_constraints",
            title="Brand and copy constraints",
            knowledge_type=KnowledgeType.QUALITY_STANDARD,
            domain=KnowledgeDomain.CONTENT,
            content=BRAND_COPY_CONSTRAINTS,
            source_uri="canonical://marketsynth/content/brand_copy_constraints",
            source_hash="sha256:pack_d_brand_v1",
            version="1.0",
            authority=KnowledgeAuthority.PRODUCT,
            locale="en",
            tags=("content", "brand", "factuality", "constraints"),
            specialist_roles=("content_specialist",),
            citation_required=False,
            pack="D",
        ),
        PackSeed(
            code="ms.content.factcheck_assumptions",
            title="Fact-checking and assumptions policy",
            knowledge_type=KnowledgeType.CONSTITUTIONAL_POLICY,
            domain=KnowledgeDomain.CONTENT,
            content=FACTCHECK_ASSUMPTIONS,
            source_uri="canonical://marketsynth/content/factcheck_assumptions",
            source_hash="sha256:pack_d_factcheck_v1",
            version="1.0",
            authority=KnowledgeAuthority.CONSTITUTIONAL,
            locale="en",
            tags=("content", "factcheck", "assumptions", "insufficient_data"),
            specialist_roles=("content_specialist", "*"),
            citation_required=False,
            pack="D",
        ),
    ]


INGESTION_MANIFEST_V1: list[dict[str, Any]] = [
    {
        "source_uri": seed.source_uri,
        "source_hash": seed.source_hash,
        "split_policy": "atomic_single_item",
        "knowledge_item_code": seed.code,
        "target_locale": seed.locale,
        "authority": seed.authority.value,
        "reviewer": "h2.3_curated_pack",
        "status": KnowledgeItemStatus.APPROVED.value,
        "reason": f"Pack {seed.pack} — curated content.telegram_post foundation",
        "pack": seed.pack,
    }
    for seed in approved_content_pack_seeds()
]

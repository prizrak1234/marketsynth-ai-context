# YANDEX-DIRECT-AD-FORMAT-SELECTOR-01 — Product Architecture (accepted, not implemented)

**Status:** `architecture_accepted` · **Implementation:** blocked until Campaign Plan architecture + PRE-LAUNCH gate are accepted  
**Priority queue:** 1 [REAL-RESEARCH-HARDENING-02](./EVIDENCE-FUNNEL-ARCHITECTURE.md) → 2 [PRE-LAUNCH-READINESS-01](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) → 3 Campaign Plan → **4 Campaign Mode Selector** → 5 [Ad Format Selector](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) → 6 Yandex Direct Execution  
**Methodology source:** Yandex Direct lesson — six ad format types (reference only; not a static «справочник форматов» in product UI)

## Product thesis

> Тип объявления выбирается не по вкусу специалиста, а по **объекту продвижения**, **доступным данным**, **площадке показа** и **цели кампании**.

Marketsynth does **not** ask: «Какой тип объявления хотите создать?»  
Marketsynth answers: **«Какой формат подходит вашему проекту — и почему остальные заблокированы.»**

This module is a **decision layer**, not a Yandex Direct UI mirror. It connects strategy, readiness, assets, and provider capabilities to a **ranked recommendation** with explicit blockers.

## Position in commercial flow

```
Business Validation (BIV)
  → Research + Evidence + Verdict
  → Marketing Strategy
  → Pre-Launch Readiness Gate
  → Campaign Plan / Campaign Architecture
  → CAMPAIGN MODE + OBJECTIVE SELECTION     ← YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01
  → AD FORMAT SELECTION                    ← this module
  → Creative Generation (format-aware)
  → Human Approval
  → Yandex Direct Execution
  → Measurement + Recheck
```

**Hard boundaries:**

| Layer | In scope | Out of scope |
|-------|----------|--------------|
| BIV / Research Engine | Segments, offer, verdict, evidence | Ad format choice |
| Pre-Launch Readiness | Site, analytics, economics, gate | Direct API calls |
| Campaign Plan | Goals, budget, channels, structure | Creative production |
| **Ad Format Selector** | Format eligibility + recommendation | Campaign creation in Direct |
| Yandex Direct Execution | API / operator launch | Strategy without readiness |

**Do not** implement format selection inside Research Engine or BIV.  
**Do not** open before Campaign Plan defines campaign goal, promotion object, and channel intent.

## Six format families (provider taxonomy)

Internal enum maps to Yandex Direct product families. Names are **stable product codes**; display labels follow provider locale.

| Code | Display (RU) | Placements | Creation mode | Promotion object |
|------|--------------|------------|---------------|------------------|
| `text_graphic` | Текстово-графические | Search, RSYA, product gallery, Maps (partial) | Manual | Product, service, brand, offer |
| `graphic` | Графические | RSYA only | Manual banner | Product, service, brand |
| `product` | Товарные | Search, RSYA, product gallery | Auto from site/feed | Single SKU / product card |
| `catalog_page` | Страницы каталога | Search, RSYA, product gallery | Auto from site/feed | Category, collection, service group |
| `neural` | Нейрообъявления | Search, RSYA | Auto from page URL | Page content (generated variants) |
| `combinatorial` | Комбинаторные | Search, RSYA, product gallery, Maps | Manual elements + auto-combine | Product, service, brand |

**Key distinction (product vs catalog):**

- `product` → individual item / card  
- `catalog_page` → category or curated selection landing

## Selection model (four axes)

Every recommendation must cite all four axes from the lesson methodology:

1. **Where shown** (`placements[]`)
2. **How created** (`creation_mode`: manual | feed | url_neural | combinatorial)
3. **What is promoted** (`promotion_object`: offer | product | category | brand | page)
4. **Campaign goal fit** (`campaign_goal`: search_demand | reach | retargeting | ecommerce_sales | catalog_discovery | creative_testing)

Generic claims from training material («подходит всем», «максимально эффективно») are **forbidden** in product copy unless backed by project-specific rationale + confidence.

## Core contract: `AdFormatRecommendation`

Add to `app/schemas/contracts.py` before implementation.

```python
# Conceptual — exact field names at implementation time

AdFormatRecommendation:
  format: AdFormatKind                    # enum above
  provider: str = "yandex_direct"
  campaign_goal: CampaignGoalKind
  promotion_object: PromotionObjectKind
  placements: list[AdPlacementKind]
  creation_mode: AdCreationModeKind
  prerequisites: list[AdFormatPrerequisite]
  strengths: list[str]                    # customer-safe, no snake_case
  limitations: list[str]
  risks: list[str]
  required_assets: list[RequiredAsset]
  required_tracking: list[str]              # e.g. metrica_goals, ecommerce_purchase
  recommended: bool                        # primary vs secondary vs blocked
  rank: int                                # 1 = primary
  confidence: float                         # 0..1, calculated not vibes
  rationale: str                            # customer-facing paragraph
  blocking_reasons: list[AdFormatBlocker]  # empty if recommended
  evidence_ids: list[UUID]                  # link to strategy/readiness/audit
  rules_version: str                        # e.g. yandex_direct_ad_formats_2026-07
```

### Supporting types

- `AdFormatPrerequisite` — code, label_ru, satisfied, verification_source  
- `RequiredAsset` — asset_type (headline, text, image, video, feed, logo), min_count, quality_gate  
- `AdFormatBlocker` — code, severity, message_ru, fix_action, owner_hint  
- `AdFormatSelectionReport` — project_id, campaign_plan_id, primary[], secondary[], blocked[], generated_at, human_approved, approval_audit_id

## Per-format recommendation logic

### `text_graphic` — recommend when

- Service or small assortment (not large catalog-first)
- Search demand is primary channel
- Concrete offer exists (from BIV / strategy)
- No quality product feed
- Need manual control over message match

**Strengths:** flexibility, Search + RSYA coverage  
**Weaknesses:** manual creative burden; quality depends on copy/design

### `graphic` — recommend when

- Goal is reach, brand awareness, or retargeting
- Quality visuals available
- Offer understandable without long copy
- Site + analytics readiness passed (Pre-Launch)

**Risk:** beautiful banner without strong offer → spend without conversion

### `product` — recommend when

- Ecommerce business model
- Valid structured feed (prices, stock, images, URLs)
- Purchase conversion trackable
- Promotion object = individual SKU

**Hard dependency:** feed quality = ad quality

### `catalog_page` — recommend when

- Large assortment; user chooses from category first
- Category landing pages exist and convert
- Structured catalog / feed at category level
- Promotion object = category or collection

**Not** a substitute for broken category UX

### `neural` — recommend only when

All of:

- Site passed content audit (Pre-Launch Website Readiness)
- First screen + UTP clear; no contradictory promises
- Prices and legal claims current
- Human approval workflow for generated variants
- Variation cap configured
- Moderation queue enabled

**Risk:** weak site → scaled weak offer. **Default: blocked** until audit PASS.

### `combinatorial` — recommend when

- ≥5 headlines, ≥3 texts, ≥4 images (thresholds configurable, versioned)
- Assets are distinct (not duplicates)
- Sufficient traffic budget for combination tests
- Conversion goals configured in analytics
- Goal includes creative testing / CVR improvement

**Risk:** combinatorial optimization on weak inputs optimizes mediocrity

## Blocking matrix (hard gates)

### `product` — blocked if

- No product feed
- Stale prices or broken product URLs
- Stock/availability not in feed
- No ecommerce analytics / purchase goal
- Non-ecommerce business model

### `catalog_page` — blocked if

- Categories mixed or unstructured
- Category landings missing or non-converting (audit finding)
- Filters/navigation broken on category pages
- Feed lacks category-level URLs

### `neural` — blocked if

- Website audit not PASS or content audit incomplete
- Contradictory or legally sensitive claims on page
- Human approval for generated ads disabled
- Stale page content (readiness recheck failed)
- Owner has not accepted neural format risk disclosure

### `combinatorial` — blocked if

- Below minimum asset counts
- Creatives near-duplicate (similarity threshold)
- Traffic/budget below minimum test volume (from Campaign Economics)
- No conversion goals configured

### `graphic` — blocked if

- No display-quality visuals
- Pre-Launch NOT_READY
- Goal is pure search-intent capture without brand layer (warn, may secondary-block)

### Global blockers (any format)

- Pre-Launch `NOT_READY`
- BIV `HOLD` / `NO_GO` (upstream)
- Yandex Direct account / format unavailable (provider capability)
- Region or legal restriction on format

## Customer-facing output (not a format catalog)

User receives **one primary + optional secondary + explicit blocked list**.

Example:

```
Основной формат: Текстово-графические объявления

Почему:
Вы продвигаете услугу с ограниченным ассортиментом.
Основной спрос — в Поиске. Товарный фид отсутствует.

Дополнительно (после подготовки):
Комбинаторные объявления — когда будут 5 заголовков, 3 текста, 4 изображения.

Не рекомендуется:
• Товарные — нет товарного фида
• Нейрообъявления — сайт не прошёл content audit
```

UI shows **rationale + fix actions**, not raw enum codes.

## Inputs (required at selection time)

| Source | Fields used |
|--------|-------------|
| BIV / Strategy | Business model, offer, segments, goal hypothesis |
| Pre-Launch Readiness | Website audit, analytics plan, economics, gate status |
| Campaign Plan | campaign_goal, budget, channel mix, promotion_object, region |
| Asset inventory | Headlines, texts, images, video, feed URLs |
| Provider capability | Account features, format availability, API version |

**Missing input → lower confidence + blocker**, not silent default to `text_graphic`.

## Provider capability discovery

Before recommending a format:

1. Resolve Yandex Direct account capabilities (API or operator checklist)
2. Map provider feature flags → internal `AdFormatKind`
3. If format unavailable for account → `blocked` with `provider_format_unavailable`
4. Cache capability snapshot with `capability_checked_at` + TTL

Architecture must allow **rule updates** without redeploying strategy logic:

- `rules_version` on every report
- Versioned JSON rules in repo (`knowledge/yandex_direct/ad_format_rules/`) — not hardcoded strings in UI
- Fallback: if provider discovery fails → recommend only `text_graphic` with `confidence ≤ 0.5` + human approval required

## Human approval

| Format | Approval rule |
|--------|----------------|
| `text_graphic`, `graphic`, `combinatorial` | Standard campaign approval |
| `product`, `catalog_page` | Feed validation sign-off |
| `neural` | **Mandatory** preview of sample generated ads + explicit owner accept |
| Any launch | Pre-Launch READY or documented override |

Approval is logged: `approval_audit_id`, timestamp, actor, rules_version.

## Relationship to Campaign Plan

Campaign Plan produces:

- `campaign_goal`
- `promotion_object` + object_ref (URL, feed_id, category_id)
- Channel intent (Search-heavy vs RSYA-heavy)
- Budget scenario + minimum test volume

Ad Format Selector **consumes** Campaign Plan **and** [Campaign Mode Selector](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md) output; it does not replace them.

Future slice: Campaign Plan UI step **«Формат объявлений»** renders `AdFormatSelectionReport`.

## SWOT (architecture)

| | |
|--|--|
| **Strengths** | Removes Direct expertise burden; explains choice; ties format to readiness; reduces wrong launch type; feeds creative generation |
| **Weaknesses** | Provider rules change; account-level variance; needs fresh docs + capability probe |
| **Opportunities** | Auto creative pack per format; media plan cost estimate; multi-format test plan; A/B orchestration |
| **Risks** | Stale taxonomy; recommend unavailable format; neural scale without audit; product ads on bad feed |

## Implementation slices (when unblocked — do not start now)

1. Contracts in `contracts.py` (`AdFormatKind`, `AdFormatRecommendation`, report types)
2. Versioned rules pack + evaluator service (pure functions, testable)
3. Input aggregator (Campaign Plan + Pre-Launch + asset inventory)
4. Provider capability adapter (Yandex Direct — read-only discovery)
5. Blocker engine + confidence calculator
6. API: `GET .../campaign-plans/{id}/ad-format-recommendations`
7. Campaign Plan UI section (recommendation card, not six-tile picker)
8. Creative generation hooks (`required_assets` → asset tasks)
9. Launch guard: execution forbidden if primary format blocked or neural without approval
10. Tests: eligibility matrix fixtures + golden recommendations per business archetype
11. Owner browser acceptance on 3 archetypes: service, ecommerce, large catalog

## Definition of done (implementation)

- User sees **primary recommendation + rationale**, not six equal cards
- Every blocked format has **specific fix action**
- Neural blocked until content audit + human approval path exists
- Product/catalog blocked without feed validation
- Combinatorial blocked without asset minimums
- Provider unavailable formats never shown as recommended
- `rules_version` + capability snapshot on every report
- No implementation in Research Engine or BIV
- Browser E2E on recommendation screen; owner acceptance

## Commercial classification

**Priority A (direct revenue)** — prevents wrong ad format spend; enables «Campaign architecture» SKU; prerequisite for Yandex Direct execution module.

**Frozen until:**

1. [REAL-RESEARCH-HARDENING](./RESEARCH-PIPELINE-HARDENING.md) owner PASS  
2. [PRE-LAUNCH-READINESS-01](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) implementation accepted  
3. Campaign Plan architecture accepted  

**Do not** parallelize with QA-01, Research hardening, or Direct API execution.

## Cross-references

- [PRE-LAUNCH-READINESS-01-ARCHITECTURE.md](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) — website/content audit gates neural; analytics gates product/combinatorial  
- [REAL-RESEARCH-READINESS.md](./REAL-RESEARCH-READINESS.md) — evidence for strategy inputs, not format rules  
- [YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md) — upstream mode + objective layer
- [USER-JOURNEY-READINESS-MATRIX.md](./USER-JOURNEY-READINESS-MATRIX.md) — update when Campaign Plan + format step added to journey

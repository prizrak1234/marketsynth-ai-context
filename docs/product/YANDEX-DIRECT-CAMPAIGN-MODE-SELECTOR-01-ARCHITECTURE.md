# YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01 — Product Architecture (accepted, not implemented)

**Status:** `architecture_accepted` · **Implementation:** blocked until Campaign Plan + PRE-LAUNCH gate are accepted  
**Priority queue:** 1 [REAL-RESEARCH-HARDENING-02](./EVIDENCE-FUNNEL-ARCHITECTURE.md) → 2 [PRE-LAUNCH-READINESS-01](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) → 3 Campaign Plan → **4 Campaign Mode Selector** → 5 [Ad Format Selector](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) → 6 Yandex Direct Execution  
**Methodology source:** Yandex Direct lesson — три режима запуска + сценарии Мастера (reference only; not a UI catalog)

## Product thesis

> Marketsynth выбирает не только **что показывать** (формат объявления), но и **в каком режиме запускать кампанию**, **с какой степенью автоматизации** и **под какую бизнес-задачу**.

Marketsynth does **not** ask: «Создать кампанию в Мастере или в ЕПК?»  
Marketsynth answers: **«Рекомендуемый режим — Мастер кампаний / Конверсии; Expert заблокирован до настройки целей и бюджета.»**

This module is a **dual decision layer**:

1. **Campaign Mode Selector** — уровень управления (automation vs control)  
2. **Campaign Objective Selector** — бизнес-сценарий и стратегия оптимизации

Together they form the **Campaign Architect** input for Yandex Direct — not a mirror of the Direct UI menu.

---

## Two axes of choice (methodology)

### Axis 1 — Management mode (automation ↔ control)

```
Простой старт          Мастер кампаний          Режим эксперта
(Fast Launch)     →    (balanced default)   →   (Controlled Performance)
less control              mid control               full control
more automation           guided automation         manual / EPC structure
```

### Axis 2 — Business objective (what the campaign optimizes for)

| Code | Display (RU) | Primary intent |
|------|--------------|----------------|
| `traffic` | Трафик / переходы | Clicks, visits |
| `conversions` | Конверсии | Leads, purchases, goals |
| `product_sales` | Товарная кампания | Ecommerce SKU + categories |
| `marketplace_sales` | Продажи на маркетплейсах | Yandex Market, Ozon, WB, Avito |
| `telegram_subscribers` | Подписчики Telegram | Channel growth via promo + bot |
| `business_without_site` | Бизнес без сайта | Auto landing from description |
| `specialist_promotion` | Продвижение специалистов | Profile-based services |
| `messenger_ads` | Реклама в мессенджерах | Telegram channels, MAX, partner network |
| `outdoor` | Наружная реклама | OOH, hyperlocal reach |
| `connected_tv` | Connected TV | Brand / reach on CTV |
| `search_banner` | Контекстный баннер на поиске | Brand / promo on SERP sidebar |

**Selection is always a combination:**

```
Management mode + Objective + Promotion object + Channel + Analytics readiness + Budget sufficiency
```

Generic training claims («минимум 10 конверсий в неделю», «не менять кампанию неделю») are **BenchmarkHint** only when tagged with provider, account, region, date — never hard-coded universal rules.

---

## Position in commercial flow

```
Business Validation (BIV)
  → Research + Evidence + Verdict
  → Marketing Strategy
  → Pre-Launch Readiness Gate
  → Campaign Plan / Campaign Architecture
  → CAMPAIGN MODE SELECTION              ← this module (mode + objective)
  → Ad Format Selection                  ← YANDEX-DIRECT-AD-FORMAT-SELECTOR-01
  → Creative Generation
  → Human Approval
  → Yandex Direct Execution
  → Measurement + Recheck
```

**Hard boundaries:**

| Layer | In scope | Out of scope |
|-------|----------|--------------|
| Campaign Plan | Goals, budget, segments, channel intent | Direct API |
| **Campaign Mode Selector** | Mode + objective eligibility + recommendation | Ad creative production |
| Ad Format Selector | Ad format family per objective | Campaign structure in Direct |
| Pre-Launch Readiness | Site, analytics, economics gate | Mode UI in Direct |
| Yandex Direct Execution | Launch operator / API | Strategy invention |

**Do not** implement inside BIV, Research Engine, or Fetch layer.  
**Do not** open before Campaign Plan defines promotion object and commercial goal.

---

## Layer 1 — Management modes

Internal codes map to Yandex Direct product surfaces. Product display names are customer-safe.

| Code | Product label (RU) | Yandex surface | Automation | Control |
|------|-------------------|----------------|------------|---------|
| `simple_start` | **Fast Launch** | Простой старт | High | Low |
| `campaign_wizard` | **Мастер кампаний** | Campaign Wizard | Medium | Medium |
| `expert_mode` | **Controlled Performance** | Режим эксперта / ЕПК | Low | High |

### `simple_start` (Fast Launch)

**Provider behavior:** URL + business description → auto ads, placements, budget split; Search + RSYA + Maps.

**Recommend when:**

- Single product or service
- Small budget; simple geography
- No in-house marketer; analytics minimal
- Client accepts limited transparency
- Speed to first impression > fine control

**Limitations (product copy, not hidden):**

- No bulk operations
- Simplified statistics
- Limited explainability of algorithm decisions
- Not suitable for multi-segment performance systems

**Risks:** weak offer scaled automatically; wrong optimization target; opaque changes

**Product warning (required in UI):** «Высокая автоматизация, ограниченная управляемость и прозрачность.»

### `campaign_wizard` (default for most Marketsynth clients)

**Provider behavior:** Site/product URL analysis → keywords, texts, images, budget options; scenario picker (conversions, products, marketplace, Telegram, etc.).

**Recommend when:**

- Site or landing ready (or explicit no-site scenario selected)
- Analytics configured **or** objective does not require conversion optimization
- Clear commercial goal from Campaign Plan
- Balance of automation and control desired
- Client not ready for EPC complexity

**Default recommendation** for post-readiness SMB/SaaS unless expert prerequisites met.

### `expert_mode` (Controlled Performance)

**Provider behavior:** Unified Performance Campaign (ЕПК) — campaign / ad group / ad levels; placements, strategies, feeds, retargeting, schedules.

**Recommend when:**

- Multiple segments or geographies
- Significant budget; complex funnel
- Conversion data accumulated; goals verified
- Need separate groups, strategies, audit trail
- Human specialist or AI-supervisor oversight

**Hard dependency:** Pre-Launch `READY` or documented override; analytics goals for conversion strategies.

**EPC structure (reference for future execution slice):**

| Level | Configures |
|-------|------------|
| Campaign | Placements, strategy, budget, schedule, global params |
| Ad group | Geo, autotargeting, keywords, interests, audiences, retargeting, content type |
| Ad | Ad format, headlines, media, extensions, feeds, filters |

---

## Layer 2 — Campaign objectives

### Core performance objectives

#### `traffic`

- **Optimization:** max clicks / visits  
- **When:** awareness of offer, no conversion tracking yet, explicit traffic goal  
- **Block conversion strategy** if goals not configured  
- **Risk:** paying for clicks without measurable business outcome

#### `conversions`

- **Optimization:** target actions (forms, calls, purchases)  
- **When:** Metrica/goals live; minimum data threshold met (versioned rule)  
- **Requires:** `required_tracking`: goal IDs, attribution honesty  
- **Risk:** premature conversion optimization on < N events/week → unstable learning

#### `product_sales`

- **When:** ecommerce; feed or site catalog; product/card URLs  
- **Placements:** Search, RSYA, product gallery  
- **Requires:** feed validation, purchase goal, learning budget  
- **Note:** campaigns need learning period — changes frequency capped in **recommendation**, not absolute rule

#### `marketplace_sales`

- **Platforms:** Yandex Market, Ozon, WB, Avito (capability-dependent)  
- **Requires:** marketplace URL, sales data passthrough where available; Ozon API key when required  
- **Risk:** pay-for-result scenarios vary by account/region — verify via capability discovery

### Channel-specific objectives

#### `telegram_subscribers`

- Channel analysis → ads → promo page → subscription via bot  
- **Marketsynth relevance:** aligns with existing Telegram product track  
- **Requires:** channel URL, bot/subscription tracking, creative uniqueness  
- **Risk:** post-edit limitations; creative must be final before launch

#### `business_without_site`

- Auto landing from business description + contacts  
- **When:** no site; local service; readiness on **input quality** not site audit  
- **Block if:** description vague; no contact method; legal claims unverified

#### `specialist_promotion`

- Profile-based services (masters, freelancers)  
- **Block if:** platform cannot pass profile data to Direct (provider capability)

#### `messenger_ads`

- Telegram channels, MAX, Yandex partner network  
- Post-like format: image/video, headline, link, ad label  
- **Upper-mid funnel**; not default for pure lead-gen without readiness

### Media / upper-funnel objectives

#### `outdoor`, `connected_tv`, `search_banner`

- **Intent:** reach, brand, hyperlocal / SERP visibility  
- **Not** default performance path for CWF.1 Launch Pack  
- **Require:** separate media budget model; OTS / brand KPIs; Pre-Launch economics  
- **Default:** secondary or blocked until Campaign Plan explicitly requests brand/reach

---

## Core contracts (add to `contracts.py` before implementation)

### `CampaignModeRecommendation`

```python
CampaignModeRecommendation:
  mode: CampaignManagementModeKind       # simple_start | campaign_wizard | expert_mode
  provider: str = "yandex_direct"
  product_label_ru: str                  # Fast Launch | Мастер кампаний | Controlled Performance
  automation_level: float                # 0..1
  control_level: float                   # 0..1
  required_expertise: str                # none | basic | specialist
  prerequisites: list[CampaignPrerequisite]
  limitations: list[str]
  risks: list[str]
  recommended_for: list[str]             # customer-safe scenarios
  recommended: bool
  rank: int
  confidence: float
  rationale: str
  blocking_reasons: list[CampaignModeBlocker]
  evidence_ids: list[UUID]
  rules_version: str
```

### `CampaignObjectiveRecommendation`

```python
CampaignObjectiveRecommendation:
  objective: CampaignObjectiveKind
  primary_conversion: str | None         # goal event label, not internal ID in customer copy
  placements: list[str]
  optimization_strategy: str             # e.g. max_conversions | max_clicks
  required_tracking: list[str]
  minimum_data: MinimumDataRequirement | None   # versioned, provider-tagged
  minimum_budget: BudgetHint | None
  required_assets: list[RequiredAsset]
  expected_learning_period_days: int | None
  risks: list[str]
  recommended: bool
  blocked: bool
  blocking_reasons: list[CampaignObjectiveBlocker]
  rationale: str
  rules_version: str
```

### `CampaignArchitectureReport`

Combined output for Campaign Plan UI:

```python
CampaignArchitectureReport:
  project_id: UUID
  campaign_plan_id: UUID
  primary_mode: CampaignModeRecommendation
  secondary_modes: list[CampaignModeRecommendation]
  primary_objective: CampaignObjectiveRecommendation
  secondary_objectives: list[CampaignObjectiveRecommendation]
  mode_objective_matrix_note: str         # why this pair
  ad_format_report_id: UUID | None        # filled after Ad Format Selector runs
  human_approved: bool
  approval_audit_id: UUID | None
  generated_at: datetime
```

---

## Recommendation logic

### Mode selection

| Condition | Mode |
|-----------|------|
| Single offer, small budget, no analyst, accepts low control | `simple_start` |
| Site ready, goal clear, analytics OK or traffic-only goal | `campaign_wizard` **(primary default)** |
| Multi-segment, large budget, goals + history, needs EPC | `expert_mode` |
| Pre-Launch NOT_READY | **all modes blocked** except documented override |
| BIV HOLD / NO_GO | upstream block |

### Objective selection (examples)

| Business model | Object | Analytics | Objective |
|----------------|--------|-----------|-----------|
| SaaS subscription | site | goals live | `conversions` |
| Ecommerce catalog | feed | purchase goal | `product_sales` |
| Marketplace seller | Ozon shop | API configured | `marketplace_sales` |
| Telegram channel | channel URL | bot tracking | `telegram_subscribers` |
| Local master, no site | profile | platform data | `specialist_promotion` or `business_without_site` |
| Brand campaign | brand | reach KPI | `connected_tv` / `outdoor` (secondary) |

### Mode × objective compatibility matrix (non-exhaustive)

| Objective | simple_start | campaign_wizard | expert_mode |
|-----------|:------------:|:---------------:|:-----------:|
| traffic | ✅ | ✅ | ✅ |
| conversions | ⚠️ goals required | ✅ | ✅ |
| product_sales | ⚠️ limited control | ✅ | ✅ |
| marketplace_sales | ⚠️ | ✅ | ✅ |
| telegram_subscribers | ⚠️ | ✅ | ⚠️ |
| business_without_site | ✅ | ✅ | ⚠️ |
| specialist_promotion | ⚠️ | ✅ | ✅ |
| messenger_ads | ❌ | ✅ | ✅ |
| outdoor / CTV / search_banner | ❌ | ⚠️ | ✅ |

⚠️ = allowed with prerequisites or secondary recommendation; ❌ = blocked or not recommended.

---

## Blocking matrix

### Global blockers

- Pre-Launch `NOT_READY` (except explicit override + audit)
- BIV `HOLD` / `NO_GO`
- Yandex Direct account unavailable (capability discovery)
- Region / legal restriction

### `simple_start` blocked if

- Client requires audit trail / multi-segment control
- Multiple products or geographies with different offers
- Conversion optimization required but analytics missing
- Expert mode prerequisites met and budget supports EPC

### `expert_mode` blocked if

- Analytics goals not configured (for conversion objectives)
- Insufficient budget for learning (economics module)
- No human approval for Controlled Performance
- Single-offer small pilot where wizard suffices (warn, not hard block)

### `conversions` objective blocked if

- No conversion goals in Metrica / analytics plan
- Insufficient historical events (versioned minimum — **BenchmarkHint**)
- Traffic-only goal explicitly chosen in Campaign Plan

### `product_sales` / `marketplace_sales` blocked if

- No feed / catalog / marketplace link
- Feed validation failed (same gates as Ad Format Selector)
- Purchase tracking unavailable

### `telegram_subscribers` blocked if

- No channel URL; bot tracking not configured
- Human has not approved Telegram ad creative constraints

### `specialist_promotion` blocked if

- Profile data cannot be transmitted to Direct (capability probe)

### Media objectives blocked if

- Campaign Plan goal is performance lead-gen only
- No brand/reach budget scenario in economics plan

---

## Customer-facing output

User receives **primary mode + primary objective + blocked alternatives** — not three equal tiles × eleven scenarios.

Example:

```
Режим: Мастер кампаний
Цель: Конверсии (заявки на SaaS)

Почему:
Сайт прошёл readiness, цели Метрики настроены, один основной сегмент,
бюджет достаточен для обучения, но структура ЕПК пока избыточна.

Не рекомендуется:
• Простой старт — нужна прозрачность по конверсиям
• Expert / ЕПК — один сегмент; вернёмся при масштабировании
• Товарная кампания — нет ecommerce-фида
```

---

## Relationship to Ad Format Selector

| Module | Question |
|--------|----------|
| **Campaign Mode Selector** | *How* to run (automation, structure, optimization target) |
| **Ad Format Selector** | *What* ad format (text-graphic, product, neural, …) |

**Order:** Mode + Objective **first** → Ad Format **second** (format depends on objective and mode capabilities).

Example: `product_sales` + `campaign_wizard` → likely `product` + `catalog_page` formats; `traffic` + `simple_start` → limited format choice with disclosure.

Cross-reference: [YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md)

---

## Provider capability discovery

Every rule must carry:

- `provider`: yandex_direct  
- `rules_version`: e.g. `yandex_direct_campaign_modes_2026-07`  
- `account_capability`: feature flags from API or operator checklist  
- `region`, `campaign_type`, `effective_date`, `source`

Before recommending mode or objective:

1. Probe account features (wizard scenarios available, EPC access, marketplace connectors)  
2. Map to internal enums  
3. Unavailable → `blocked` with `provider_scenario_unavailable`  
4. Cache snapshot + TTL on report

**Fallback:** if discovery fails → recommend `campaign_wizard` + `traffic` with `confidence ≤ 0.5` + mandatory human approval (never default to `simple_start` silently).

---

## Human approval

| Mode / objective | Approval |
|------------------|----------|
| `simple_start` | Explicit accept of limited control disclaimer |
| `campaign_wizard` | Standard campaign approval |
| `expert_mode` | Controlled Performance acknowledgment + readiness sign-off |
| `conversions` | Goals verified in analytics plan |
| `telegram_subscribers` | Creative finality warning |
| Media objectives | Brand budget + KPI sign-off |

Logged: `approval_audit_id`, actor, timestamp, `rules_version`.

---

## Mode switching rules (post-launch, architecture only)

| Transition | Allowed when |
|------------|--------------|
| simple_start → wizard | Client needs more control; export learning data if provider allows |
| wizard → expert | Segments multiply; budget up; analytics mature |
| expert → wizard | Simplification requested; human decision + audit |
| Any → simple_start | **Discouraged** if conversion tracking was primary — warn on data loss |

No automatic downgrade without human confirmation.

---

## SWOT

| | |
|--|--|
| **Strengths** | Separates automation from expert; links campaign to business goal; maturity ladder; Telegram/marketplace paths; foundation for Campaign Architect |
| **Weaknesses** | Account-dependent features; Direct UI renames; hidden auto logic; conversion rules need live data |
| **Opportunities** | Auto readiness check; optimization strategy picker; min budget forecast; performance vs media routing; EPC structure draft |
| **Risks** | Launch without analytics; traffic vs conversions mismatch; budget too low for learning; scaling weak offer in auto mode |

---

## Implementation slices (when unblocked — do not start now)

1. Contracts: `CampaignManagementModeKind`, `CampaignObjectiveKind`, recommendation types  
2. Versioned rules pack (`knowledge/yandex_direct/campaign_modes/`)  
3. Input aggregator: Campaign Plan + Pre-Launch + economics + capability snapshot  
4. Mode evaluator + objective evaluator (pure functions)  
5. Compatibility matrix engine  
6. API: `GET .../campaign-plans/{id}/campaign-architecture`  
7. Campaign Plan UI: **«Режим и цель кампании»** card  
8. Wire output to Ad Format Selector input  
9. Launch guard: execution forbidden if mode/objective blocked  
10. Tests: archetype fixtures (SaaS, ecommerce, Telegram, no-site, specialist)  
11. Owner acceptance on 3 archetypes in browser  

---

## Definition of done (implementation)

- User sees **one primary mode + one primary objective + rationale**  
- Fast Launch shows **automation warning**  
- Expert blocked without readiness + analytics where required  
- Conversions blocked without goals  
- Every blocked option has **specific fix action**  
- Provider unavailable scenarios never shown as recommended  
- `rules_version` + capability snapshot on every report  
- Ad Format Selector consumes architecture report  
- No implementation in BIV / Research / Fetch layers  
- Browser E2E; owner acceptance  

---

## Commercial classification

**Priority A** — prevents wrong campaign type and automation level; enables Campaign Architect SKU; prerequisite chain for Direct execution.

**Frozen until:**

1. [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md) (HARDENING-02) owner PASS  
2. PRE-LAUNCH-READINESS-01 implementation accepted  
3. Campaign Plan architecture accepted  

**Do not** parallelize with HARDENING-02 implementation, QA-01, or Direct API work.

---

## Cross-references

- [YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) — downstream format layer  
- [PRE-LAUNCH-READINESS-01-ARCHITECTURE.md](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) — gates expert + conversions  
- [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md) — active P0; blocks all execution tracks  
- [USER-JOURNEY-READINESS-MATRIX.md](./USER-JOURNEY-READINESS-MATRIX.md) — update when Campaign Architect step added  

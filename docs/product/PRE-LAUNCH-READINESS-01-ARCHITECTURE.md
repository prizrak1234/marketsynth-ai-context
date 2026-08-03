# PRE-LAUNCH-READINESS-01 — Product Architecture (accepted, not implemented)

**Status:** `architecture_accepted` · **Implementation:** blocked until [REAL-RESEARCH-READINESS](./REAL-RESEARCH-READINESS.md) owner PASS  
**Priority queue:** 1 REAL-RESEARCH-READINESS → **2 PRE-LAUNCH-READINESS-01** → 3 Campaign Plan → 4 [Campaign Mode Selector](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md) → 5 [Ad Format Selector](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) → 6 Yandex Direct execution  
**Methodology source:** Yandex Boards «01. Подготовка сторонней инфраструктуры к запуску Яндекс Директ» (reference only — benchmarks are not universal laws)

## Product thesis

> Реклама — усилитель того, что уже есть. Нельзя усилить то, чего нет, и нельзя усилить то, что сломано.

Marketsynth positioning: **«Прежде чем потратить ваши деньги, мы поможем их сохранить.»**

PRE-LAUNCH-READINESS is **not** another report table. It is a **mandatory gate** between marketing strategy and paid campaign execution. Without it, Marketsynth launches ads onto unprepared landing pages and blames the channel for poor results.

## Canonical commercial flow (target)

```
Idea / Intake
  → Business Validation (BIV)
  → Research + Evidence + Verdict
  → Marketing Strategy
  → PRE-LAUNCH READINESS GATE          ← this module
  → Campaign Plan
  → Campaign Mode + Objective Selection   ← YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01
  → Ad Format Selection                ← YANDEX-DIRECT-AD-FORMAT-SELECTOR-01
  → Human Approval
  → Execution (Yandex Direct, etc.)
  → Measurement + Recheck
```

**Hard rules:**

- `readiness.status == NOT_READY` → **campaign launch forbidden**
- `HOLD` / `NO_GO` from BIV → advertising contour blocked upstream
- `CONDITIONALLY_READY` → launch only with **explicit human override** + audit trail
- High weighted score **does not** override a critical blocker (e.g. analytics missing)

## Separation from Business Validation

| Dimension | Business Validation (BIV) | Pre-Launch Readiness |
|-----------|---------------------------|----------------------|
| Question | «Стоит ли идти в рынок?» | «Готовы ли мы тратить бюджет на трафик?» |
| Inputs | Idea, market, competitors (research) | Strategy outputs + live infrastructure |
| Output | GO / CONDITIONAL_GO / PILOT / HOLD / NO_GO | NOT_READY / CONDITIONALLY_READY / READY |
| UI | Workspace validation / report | **Separate screen: «Готовность к запуску»** |
| Evidence | External sources, findings | Site checks, analytics probes, client-provided access |

Research engine feeds **segments, competitors, positioning hypotheses** into readiness — readiness does not invent them without evidence.

## Readiness domains (8)

| Domain | Weight | What it proves |
|--------|--------|----------------|
| Audience Readiness | 15% | Segments, portraits, JTBD, pains — not «широкая аудитория» |
| Offer Readiness | 15% | Segment-specific value prop, message, CTA, proof |
| Competitor Readiness | 10% | Occupied USPs, gaps, differentiation (tools swappable) |
| Journey Readiness | 10% | CJM stages with touchpoints, barriers, business responses |
| Website Readiness | 15% | Landing can convert traffic (audit findings, not vibes) |
| Analytics Readiness | 15% | Measurement exists before spend |
| Economics Readiness | 15% | Budget derived from business goal, margin-aware |
| Execution Readiness | 5% | Approval, minimum test budget, channel prerequisites |

**Critical gate priority:** any critical blocker → `NOT_READY` regardless of weighted score.

## Data contracts (to add in `app/schemas/contracts.py` before implementation)

### Audience & offer

- `AudienceSegment` — id, name, portrait, job_to_be_done, pains, desired_outcomes, objections, buying_role, purchase_trigger, decision_criteria, channel_preferences, evidence_ids, confidence
- `SegmentOffer` — segment_id, value_proposition, unique_mechanism, proof, benefit, objection_response, primary_message, CTA, evidence_ids, confidence

### Customer journey

- `CustomerJourney` — project-scoped, versioned, linked to strategy run
- `CustomerJourneyStage` — stage enum + customer_goal, expectations, actions, touchpoints, emotional_state, barriers, business_response, recommended_content, recommended_channel, conversion_event, owner

**Stages:** `awareness` · `search` · `evaluation` · `first_contact` · `purchase` · `delivery_or_onboarding` · `usage` · `retention`

CJM is a **strategic object** (editable, recheckable), not static report prose.

### Competitors

- `CompetitorPositioning` — competitor, occupied_claims, weaknesses, gap_opportunity, evidence_ids, confidence

### Website audit

- `WebsiteAudit` — url, domain scores, blocking_issues, readiness_score
- `WebsiteAuditFinding` — check_type, fact, evidence, business_impact, severity, recommended_fix, blocking, verification_method

**Check types:** availability · performance · mobile · first_screen · message_match · ux · forms · trust · tracking · automation

Format: **check → fact → business impact → fix → recheck** (see loft example in methodology board).

**Benchmark rule:** thresholds (e.g. «>3s = 50% bounce») are **BenchmarkHint** only when tagged with source, industry, region, date, applicability — never hard-coded universal rules.

### Analytics (provider-independent)

- `AnalyticsPlan` — provider, tracking_status, events, goals, attribution_model, revenue_tracking, consent_requirements, validation_status
- `ConversionGoal` — event_type (phone_click, email_click, form_submit, page_view, custom, revenue), configured, last_event_at, verification

**First adapter:** Yandex Metrica (counter, code, goals). Architecture must not be Metrica-only.

### Economics & KPI

- `CampaignKpiPlan` — funnel-stage metrics (impressions/CPM → clicks/CTR/CPC → CR/CPA/ROAS/ROMI) with formulas documented, not magic numbers
- `CampaignEconomics` — reverse model: revenue_target → sales → leads → visits → clicks → impressions → budget; scenarios pessimistic/base/optimistic; target_cpa, target_cac, break_even_roas, gross_margin, assumptions, confidence

**ROMI > 0 is insufficient** without margin model and attribution honesty.

### Gate & report

- `ReadinessBlocker` — code, severity (critical|high|medium), domain, message_ru, fix_action, owner, blocking
- `PreLaunchReadinessReport` — status, weighted_score, critical_count, non_critical_count, domains[], blockers[], fix_plan[], budget_scenarios[], final_recommendation, version, parent_report_id (for recheck lineage)

## Critical blockers (non-exhaustive)

Launch **forbidden** if any:

- missing audience segment
- missing segment-specific offer
- landing unavailable / mobile broken / conversion form broken
- analytics not installed OR goals not configured OR conversions unmeasurable
- target CAC/CPA unknown
- budget below minimum statistically meaningful test
- human approval missing (when required)

## Customer report sections

Executive Summary · Readiness Status · Score · Critical Blockers · Audience Segments · Offers by Segment · Competitor Positioning · Customer Journey · Website Audit · Analytics Plan · KPI Plan · Economics · Budget Scenarios · Fix Plan · Recheck Plan · Final Recommendation

## Fix plan & recheck

Each issue → `FixPlanItem`: priority, owner, action, expected_impact, acceptance_criterion, verification, dependency.

**Recheck:** new report version; compare before/after, resolved/remaining blockers, score delta, campaign eligibility. **Never overwrite** prior report.

## UI (future)

Screen: **«Готовность к запуску»** — status, score, blockers, journey map, site audit, analytics, economics, fix plan.

Button **«Подготовить кампанию»** enabled only when `READY`, or `CONDITIONALLY_READY` + explicit override modal (logged).

## Research dependency (why implementation waits)

Segments, competitor claims, USP, and parts of CJM must be **evidence-backed** from the research engine. If BIV returns 10% confidence with zero sources, readiness becomes another template generator.

**Prerequisite:** [REAL-RESEARCH-READINESS](./REAL-RESEARCH-READINESS.md) program PASS — specifically [RESEARCH-PIPELINE-HARDENING](./RESEARCH-PIPELINE-HARDENING.md) (six-stage pipeline, fetch ≥90%, evidence coverage ≥80%, citation 100%). Provider smoke alone is insufficient.

## Implementation slices (when unblocked)

1. Contracts in `contracts.py` + persistence
2. Readiness evaluator service (domain scorers + critical gate)
3. Website audit runner (bounded, client URL + optional crawl)
4. Analytics adapter — Yandex Metrica probe
5. Economics reverse calculator + scenario engine
6. API + separate UI screen
7. Campaign launch guard (403 if NOT_READY)
8. Recheck + version history
9. Browser E2E + owner acceptance (no mock)

## Definition of done (implementation)

- Module separated from BIV
- CJM per segment, editable object
- Site + analytics checked with honest limits
- Budget reverse-calculated with margin-aware ROAS
- Gate blocks campaign launch
- Critical blocker cannot be averaged away
- Fix plan + recheck + audit trail for override
- Browser E2E PASS, owner acceptance, zero critical defects

## Commercial classification

**Priority A (direct revenue)** — prevents budget waste, enables paid «Audit before launch» SKU, strengthens core positioning.

**Do not open** until REAL-RESEARCH-READINESS is owner-accepted. Do not fold into QA-01 or Campaign Plan work in parallel.

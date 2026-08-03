# Research Pipeline Hardening

**Volume:** Research Runtime  
**Program:** [REAL-RESEARCH-READINESS](./REAL-RESEARCH-READINESS.md)  
**Active slice:** `REAL-RESEARCH-HARDENING-01` — **checkpoint closed** (Fetch/Observability)  
**Next slice:** [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md) (`REAL-RESEARCH-HARDENING-02`) — **sole P0** until owner PASS  
**Status:** `hardening_01_closed` · `hardening_02_architecture_accepted`  
**Priority:** BLOCKER — QA-01, PRE-LAUNCH, Campaign Plan, Direct, and all downstream modules **frozen**

## Why this exists

Provider smoke PASS is **necessary but insufficient**. It only proves credentials and one round-trip. It does **not** prove the engine can produce commercial-grade evidence.

The Marketsynth real run (`8038e2a7`, 2026-07-28) exposed the original bottleneck at Fetch (0/32).  
Run `5eaa7519` (2026-07-28, post-HARDENING-01) exposed the **current** bottleneck at **Evidence Funnel** (40 documents → 1 accepted evidence).

```
Query → Search ✓ → Fetch ✓ (40) → Extract ✓ → Claims ✗ → Evidence ✗ (1) → Report ✗
                                              ↑
                                    HARDENING-02 focus
```

Result: 10% confidence, «рынок не подтверждён», «не удалось подтвердить конкурентов» — not a UI problem, **zero evidence collected**.

**Goal:** Harden the full pipeline so real cases yield traceable, category-coverage evidence — or honest gap disclosure with documented search attempts.

---

## Pipeline stages (canonical)

```
Discovery → Fetch → Extract → Normalize → Evidence → Reasoning → Verdict → Report
```

Each stage must emit **observable metrics** persisted on the run (see `BivRunObservability` extension plan below).

---

## Stage 1 — Discovery

**Question:** Did we find enough diverse, relevant URLs to investigate?

| Check | Requirement |
|-------|-------------|
| Query generation | Decomposed by category (market, competitors, demand, pricing, ICP, …) — not one long string |
| Search diversity | Distinct queries per category; localization (region/language) applied |
| Deduplication | Same URL/domain syndication not counted as independent |
| Localization | Russia / RU queries where intake geography requires it |

**Target metric:** ≥ **20–30 relevant candidate URLs** discovered per full research run (Marketsynth-class case).

**Code touchpoints:** `query_strategy.py`, `research_decomposition.py`, `research_cascade.py`, `skill.py` (search loop), MCP `invoke_search`.

**Failure modes to log:** empty SERP, duplicate-only results, wrong locale, query echo of intake without expansion.

---

## Stage 2 — Fetch

**Question:** Did we successfully retrieve page content for discovered URLs?

**Per-URL outcome taxonomy (required):**

| Outcome | Code |
|---------|------|
| Success | `success` |
| Timeout | `timeout` |
| HTTP 403 / 404 | `http_403`, `http_404` |
| Rate limit | `rate_limited` |
| Robots / policy block | `robots_blocked` |
| JS-only / empty body | `javascript_required`, `empty_body` |
| Unsupported content | `unsupported_mime` |
| Provider error | `provider_error` |

**Target metric:** **Fetch success rate ≥ 90%** on attempted fetches (excluding permanently invalid URLs).

**Current gap:** No per-URL fetch ledger with failure reason; run `8038e2a7` shows 32 search / **0 fetch** with silent continuation.

**Code touchpoints:** `McpClient.invoke_fetch`, `FirecrawlFetchTool`, `skill.py` fetch loop, `McpToolCallAuditTable`.

**Hardening actions (slice):**

- Persist fetch outcome per URL on run observability
- Fallback fetch provider or degraded retry policy (not «fix Firecrawl» alone — **audit + resilience**)
- Stop treating «search exhausted budget with zero fetches» as succeeded research

---

## Stage 3 — Extract

**Question:** Did fetch produce usable text for evidence extraction?

Pipeline per URL:

```
URL → raw payload → clean text → sections → metadata → citation candidates
```

| Check | Requirement |
|-------|-------------|
| Minimum text length | Body usable after sanitization (no nav soup) |
| Metadata | title, publisher, date or `date_unavailable` |
| Section signal | Identifiable claims, not menu concatenation |

**Target metric:** **Extraction success ≥ 95%** of successful fetches.

**Code touchpoints:** `sanitization.py`, `source_quality.py`, `firecrawl_fetch.py` normalized excerpt, `evidence_validation.py`.

---

## Stage 4 — Evidence

**Question:** How many **accepted** evidence items per commercial category?

Evidence is not «we found a site». Evidence is a **claim + excerpt + source + quality scores** accepted by rules.

**Category coverage targets (Marketsynth-class SaaS case):**

| Category | Minimum accepted evidence (target) |
|----------|-------------------------------------|
| Market size / existence | 3 |
| Competition | 8 |
| ICP / audience | 6 |
| Pricing | 5 |
| Demand | 12 |

Exact floors are **case-dependent**; gaps must state: what was searched, what was found, why insufficient, what action closes the gap.

**Target metric:** **Evidence coverage ≥ 80%** of required category floors OR explicit gap objects with search audit trail.

**Code touchpoints:** `evidence_validation.py`, `evidence_contract.py`, `findings.py`, `coverage_contract.py`, `skill.py` evidence loop.

---

## Stage 5 — Reasoning

**Question:** Is every high-impact claim tied to accepted evidence?

BIV pipeline today: rule-based claim extraction (no LLM in hot path). Reasoning = findings + verdict assembly from evidence only.

| Check | Requirement |
|-------|-------------|
| Finding → evidence_ids | Every non-hypothesis finding |
| No rejected evidence | Findings must not reference rejected items |
| No memory claims | Claims without evidence → hypothesis or gap, not confirmed |
| Confidence justified | Score reflects evidence count + category coverage |

**Target metrics:**

- **Citation coverage: 100%** of confirmed findings → evidence → URL
- **Hallucination: 0** unsupported high-impact claims in customer report
- **Confidence justified: 100%** — score explainable from evidence ledger

**Code touchpoints:** `findings.py`, `commercial_verdict.py`, `customer_report.py`, `real_research_readiness.py` validators.

---

## Stage 6 — Report

**Question:** Is the customer report a **consequence** of evidence, not a template?

Report builds **only after** stages 1–5 produce a defensible ledger.

| Check | Requirement |
|-------|-------------|
| No naked «не удалось подтвердить» | Must include search attempts + alternative queries tried |
| Verdict specific | GO / CONDITIONAL_GO / PILOT_ONLY / HOLD / NO_GO with rationale |
| Export clean | No DOM, empty URLs, snake_case debug |
| Sections match evidence | Market, competitors, ICP, pricing, economics, risks |

**Anti-pattern (current):** 10% confidence + boilerplate gaps without fetch audit = **pipeline FAIL**, even if API status `succeeded`.

---

## True PASS criteria (replaces provider smoke alone)

| Metric | Threshold |
|--------|-------------|
| Search success (queries returning candidates) | ≥ 95% |
| Fetch success (attempted URLs) | ≥ 90% |
| Extraction success (of successful fetches) | ≥ 95% |
| Evidence coverage (category floors or honest gaps) | ≥ 80% |
| Citation coverage (findings → evidence → URL) | 100% |
| Confidence justified (explainable from ledger) | 100% |
| Hallucination (unsupported high-impact claims) | 0 |

**Provider smoke** remains a **precondition** (credentials + reachability), not completion.

---

## Control output (owner checkpoint)

```
Pipeline: PASS | FAIL
Search success: X%
Fetch success: Y%  (attempted N, success M)
Extraction success: Z%
Evidence: market A/comp B/demand C/... (or gaps documented)
Findings: K (all cited: yes/no)
Verdict: … (confidence: …%, justified: yes/no)
Marketsynth case: completed | blocked
Hallucination flags: 0
Export: PASS | FAIL
Blocker: …
```

---

## Observability extensions (implementation)

Extend `BivRunObservability` / internal diagnostics with:

- `discovery_url_count`, `discovery_unique_domains`
- `fetch_attempted`, `fetch_succeeded`, `fetch_outcomes: dict[code, count]`
- `extraction_succeeded`, `extraction_failed`
- `evidence_by_category: dict[category, {accepted, rejected, hypothesis}]`
- `citation_coverage_percent`, `unsupported_claims_count`
- `pipeline_stage_timings`

Persist on run; surface in operator view only — not customer report.

---

## Frozen until REAL-RESEARCH PASS

Do **not** open implementation on:

- Campaign Builder / Campaign Plan
- Yandex Direct / Google Ads execution
- Telegram Campaign automation
- SEO Planner
- PRE-LAUNCH-READINESS-01 (implementation)
- HR / Legal / Sales CRM / Auto Publish

These consume research outputs. Weak evidence → automated wrong decisions.

**Allowed after architecture only (no runtime):** PRE-LAUNCH-READINESS-01 ✅ · YANDEX-DIRECT-AD-FORMAT-SELECTOR-01 ✅ · YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01 ✅

---

## Commercial flow (after PASS)

```
Business Validation → Research → Evidence → Strategy
  → Pre-Launch Readiness → Campaign Plan → Campaign Mode Selection → Ad Format Selection → Approval → Execution
```

Research PASS is the gate for everything to the right of Evidence.

---

## Definition of Done — REAL-RESEARCH-HARDENING-01

Slice complete → `waiting_for_owner_validation` only when:

1. All six pipeline stages instrumented with metrics above
2. True PASS thresholds met on **Marketsynth SaaS** real case (not mock)
3. Three real cases (Marketsynth / weak brief / weak commercial) with differentiated outcomes
4. No report with naked «не удалось подтвердить» without search audit trail
5. Human audit: 10 accepted sources, 5 rejected, 5 findings, high-impact claims traced
6. Automated tests for pipeline metrics + validators
7. Browser E2E real-provider flow PASS
8. Owner browser acceptance

Then and only then: QA-01, then PRE-LAUNCH-READINESS-01 implementation.

---

## Code map (Research Runtime)

| Stage | Primary modules |
|-------|-----------------|
| Discovery | `query_strategy.py`, `research_decomposition.py`, `research_cascade.py`, `skill.py` |
| Fetch | `mcp/client.py`, `firecrawl_fetch.py`, `xmlriver_search.py` |
| Extract | `sanitization.py`, `source_quality.py`, `relevance.py` |
| Normalize | `evidence_validation.py`, `commercial_relevance.py` |
| Evidence | `skill.py`, `evidence_contract.py`, `coverage_contract.py` |
| Reasoning | `findings.py`, `commercial_verdict.py`, `market_confidence.py` |
| Report | `customer_report.py`, `report_export.py`, `real_research_readiness.py` |

---

## Known incidents (baseline)

| Run | Search | Fetch | Docs | Accepted evidence | Verdict | Root cause |
|-----|--------|-------|------|-------------------|---------|------------|
| `8038e2a7` | 32 | 0 | 0 | 0 | HOLD 10% | Fetch total failure |
| `5eaa7519` | 32 | 40 | 40 | **1** | pipeline fail | **Evidence funnel collapse** — see [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md) |

This document defines HARDENING-01 (Fetch). Evidence Funnel is defined in HARDENING-02 architecture doc.

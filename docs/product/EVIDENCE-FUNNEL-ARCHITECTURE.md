# Evidence Funnel Architecture — REAL-RESEARCH-HARDENING-02

**Status:** `architecture_accepted` · **Implementation:** not started — **no code until owner accepts this doc**  
**Program:** [REAL-RESEARCH-READINESS](./REAL-RESEARCH-READINESS.md)  
**Prior slice:** [RESEARCH-PIPELINE-HARDENING](./RESEARCH-PIPELINE-HARDENING.md) (`HARDENING-01`) — Discovery/Fetch/Observability **closed**; bottleneck **measured**  
**Active slice:** `REAL-RESEARCH-HARDENING-02` — Evidence Extraction & Commercial Claim Pipeline  
**Priority:** **P0 BLOCKER** — QA-01, PRE-LAUNCH, Campaign Plan, Direct **frozen** until Evidence Funnel PASS

## Product thesis

> Marketsynth умеет получать интернет. Следующий барьер — **превращать интернет в знания** без ослабления integrity gates.

HARDENING-01 доказал: Search и Fetch **не** являются узким местом для Marketsynth SaaS case.  
HARDENING-02 фокусируется **исключительно** на Evidence Funnel — от HTML до customer report.

**Out of scope for HARDENING-02:**

- XMLRiver / search layer
- Firecrawl / provider layer / fetch orchestrator (кроме read-only audit replay)
- Снижение evidence floors
- Ослабление integrity rules
- Искусственное повышение coverage

---

## Measured incident (baseline for HARDENING-02)

Run `5eaa7519-6ea1-4ca1-b3e2-d5e67707cf5f` · correlation `8e14d848d05c4b64ba6b31199baa351a` · Marketsynth SaaS · 2026-07-28

| Layer | Metric | Result | Assessment |
|-------|--------|--------|------------|
| Discovery | Search success | 32/32 (100%) | ✅ |
| Fetch | Successful documents | 40/54 eligible (74%) | ⚠️ below 90% target, **sufficient for research** |
| Extract | Normalized documents | 40/45 attempts (89%) | ✅ practical |
| **Evidence Funnel** | **Accepted evidence** | **1** from 40 documents | ❌ **97.5% loss** |
| Reasoning | Findings w/ evidence | 1 | ❌ |
| Report | Customer report | not generated | blocked by pipeline |

**Failure code:** `fewer_than_3_accepted_sources`  
**Interpretation:** pipeline validation worked; **claim → evidence conversion collapsed**.

### Architecture maturity (owner assessment)

| Layer | Score |
|-------|-------|
| Research Discovery | 9.5/10 |
| Provider Layer | 8.5/10 |
| Observability | 10/10 |
| Pipeline Validation | 10/10 |
| **Evidence Funnel** | **3/10** ← sole P0 |

---

## Canonical funnel (target)

Metrics must be counted in **claims**, not only documents.

```
40 documents (successful fetch)
  ↓
~850 HTML blocks          ← DOM / structural segmentation
  ↓
~410 semantic blocks      ← main content, nav/boilerplate removed
  ↓
~190 commercial blocks    ← viability-relevant paragraphs
  ↓
~74 extracted claims      ← atomic, category-tagged candidates
  ↓
~28 validated claims      ← URL, excerpt, atomicity, non-fluff
  ↓
~17 accepted evidence     ← CONFIRMED + commercial relevance + tier gate
  ↓
~11 findings              ← traceable to evidence_ids
  ↓
customer report + verdict
```

Numbers above are **target shape** for a Marketsynth-class case — not fake targets. HARDENING-02 must **measure actual** counts per run and close gaps vs shape.

---

## Stage model (Document → Verdict)

### Stage 0 — Document (input to funnel)

**Input:** successful fetch result — HTML or markdown, URL, title, category context from research plan.

**Current code:** `BivFetchOrchestrator` → `content_extraction.extract_and_normalize_document` → `clean_text`.

**Metric:** `documents_in_funnel` (= successful unique fetches entering claim pipeline).

**HARDENING-01 baseline:** 40.

---

### Stage 1 — DOM / structural blocks

**Question:** How much raw structure survives before semantic filtering?

| Step | Description |
|------|-------------|
| Parse | Detect HTML vs plain; strip script/style/nav/aside |
| Block split | Sections by heading, article, list clusters, table rows |
| Count | `html_blocks_total`, `html_blocks_discarded_nav`, `html_blocks_discarded_empty` |

**Current gap:** no block-level ledger; extraction jumps from full body → sentences.

**Target modules (new):** `claim_pipeline/dom_segmentation.py`

---

### Stage 2 — Semantic blocks

**Question:** Which blocks contain substantive prose?

| Check | Rejection code |
|-------|----------------|
| Boilerplate / cookie / nav chrome | `semantic_boilerplate` |
| JS shell / empty | `semantic_javascript_shell` |
| Category listing without claims | `semantic_category_listing` |
| Duplicate block (fingerprint) | `semantic_duplicate_block` |
| Too short (< min chars) | `semantic_too_short` |

**Metric:** `semantic_blocks_total`, `semantic_blocks_rejected` by reason.

**Current partial code:** `content_extraction.validate_clean_content`, `remove_duplicate_blocks`.

---

### Stage 3 — Commercial blocks

**Question:** Which semantic blocks relate to **viability** (market, demand, competitors, ICP, pricing, risks)?

| Dimension | Examples |
|-----------|----------|
| `market` | market size, segment, TAM/SAM language |
| `market_size` | numeric market estimates, CAGR |
| `competitors` | named competitors, positioning |
| `demand` | adoption, willingness, search interest |
| `icp` | buyer segment, pains, jobs |
| `pricing` | subscription, ARPU, price points |
| `trend` | growth/decline signals |
| `review` | user/review sentiment (supporting only) |
| `benchmark` | comparative stats |
| `commercial_risks` | regulation, margin, CAC |
| `marketing_fluff` | hype without verifiable fact — **reject** |

**Metric:** `commercial_blocks_total`, `commercial_blocks_by_dimension`, `commercial_blocks_rejected_fluff`.

**Current partial code:** `commercial_relevance.assess_commercial_relevance` — applied **per claim**, not per block; overly late in funnel.

---

### Stage 4 — Extracted claims

**Question:** How many atomic, category-tagged claims are produced?

**Rules (unchanged integrity intent):**

- One verifiable sentence per claim
- Passes `validate_atomic_claim` (P0.4)
- Tagged with research category + commercial dimension
- Max claims per block configurable (versioned)

**Metric:** `claims_extracted_total`, `claims_extracted_by_category`, `claims_extracted_by_dimension`.

**Current code:** `extraction.extract_claims` — **known bottleneck:**

- Keyword gate per category → most blocks yield 0 claims when keyword mismatch
- Fallback: only **1** claim without keyword match
- Sentence split requires `.!?` — poor for HTML-stripped direct_http text
- Max **2** claims per document

**Rejection codes at extraction:**

| Code | Meaning |
|------|---------|
| `claim_no_category_keyword` | Keyword gate failed, fallback exhausted |
| `claim_not_atomic` | Failed atomic claim validator |
| `claim_too_short` | Below min length |
| `claim_duplicate_fingerprint` | Near-duplicate of prior claim in run |
| `claim_injection_filtered` | Prompt-injection pattern |

---

### Stage 5 — Validated claims

**Question:** Which extracted claims survive URL, excerpt, and sanitization gates?

| Check | Module (current) | Rejection code |
|-------|------------------|----------------|
| Valid source URL | `evidence_validation.is_valid_source_url` | `claim_invalid_url` |
| Non-empty excerpt | `validate_evidence_acceptance` | `claim_empty_excerpt` |
| Not navigation/boilerplate | `is_boilerplate_content`, `is_navigation_or_chrome` | `claim_boilerplate` |
| Not raw DOM markers | `_DOM_MARKERS` in readiness | `claim_raw_dom` |
| Sanitized statement | `sanitize_evidence_statement` | `claim_sanitization_failed` |

**Metric:** `claims_validated_total`, `claims_rejected_total`, `claims_rejected_by_reason: dict[str, int]`.

---

### Stage 6 — Accepted evidence

**Question:** Which validated claims become CONFIRMED/HYPOTHESIS evidence items?

| Gate | Module (current) | Rejection / downgrade |
|------|------------------|------------------------|
| Source relevance (page-level) | `relevance.assess_source_relevance` | Pre-filter before claims — **already passed for 40 docs** |
| Commercial relevance (claim-level) | `commercial_relevance.assess_commercial_relevance` | `no_commercial_domain_overlap`, `generic_audience_economy_not_product_viability`, `market_demand_without_commercial_signal` |
| Classification | `classification.classify_evidence_item` | `UNSUPPORTED_CLAIM`, tier D → reject; tier C → HYPOTHESIS |
| Source quality tier | `source_quality` | `tier_d_source_rejected`, `low_reliability` → HYPOTHESIS |
| Persistence | `skill._create_classified_evidence` | DB / contract errors |

**Metric:** `evidence_accepted`, `evidence_rejected`, `evidence_hypothesis`, `evidence_by_category`, `evidence_by_dimension`.

**Integrity rule:** `accepted=true` only for CONFIRMED path passing all gates. **Do not** lower floors to inflate counts.

**HARDENING-01 baseline:** 1 accepted (market=1); floors unmet for competition, ICP, pricing, demand.

---

### Stage 7 — Findings

**Question:** How many findings link to accepted evidence with citation coverage 100%?

| Check | Rejection |
|-------|-----------|
| No evidence_ids | `finding_without_evidence` |
| Uses rejected evidence | `finding_uses_rejected_evidence` |
| Hypothesis-only | Separate track — not counted toward confirmed findings |

**Metric:** `findings_total`, `findings_with_evidence`, `unsupported_findings`, `citation_coverage`.

**Current baseline:** 1 finding, citation 100% — scale problem, not traceability problem.

---

### Stage 8 — Report & verdict

**Question:** Does customer report reflect evidence-backed narrative?

**Blocked when:** evidence floors not met, `fewer_than_3_accepted_sources`, report validator failures.

**Metric:** `report_generated`, `report_validation_passed`, `export_validation_passed`, `category_floor_status[]`.

---

## Funnel observability contract (to add in `contracts.py`)

### Per-run aggregate: `BivClaimFunnelMetrics`

```python
# Conceptual — exact names at implementation

BivClaimFunnelMetrics:
  documents_in_funnel: int
  html_blocks_total: int
  html_blocks_rejected: dict[str, int]
  semantic_blocks_total: int
  semantic_blocks_rejected: dict[str, int]
  commercial_blocks_total: int
  commercial_blocks_by_dimension: dict[str, int]
  claims_extracted: int
  claims_extracted_by_category: dict[str, int]
  claims_validated: int
  claims_rejected_by_reason: dict[str, int]
  evidence_accepted: int
  evidence_hypothesis: int
  evidence_rejected: int
  evidence_by_category: dict[str, int]
  evidence_by_dimension: dict[str, int]
  findings_total: int
  findings_with_evidence: int
  funnel_loss_rate: float          # 1 - evidence_accepted / claims_extracted
  precision_proxy: float | None      # accepted / validated (when validated > 0)
  recall_proxy: float | None         # categories_with_floor_met / categories_required
```

### Per-claim audit row: `BivClaimAuditEntry` (persisted, operator-only)

```python
BivClaimAuditEntry:
  run_id: UUID
  document_id: UUID
  source_url: str
  research_category: str
  commercial_dimension: str
  stage_reached: str               # last stage before accept/reject
  rejection_reason: str | None
  claim_text_hash: str              # no full text in logs if policy requires
  excerpt_len: int
  accepted: bool
  evidence_id: UUID | None
```

**Rule:** Every rejected claim **must** have exactly one primary `rejection_reason` from the taxonomy above.

---

## Category & dimension coverage

Evidence floors (unchanged — **do not lower**):

| Category | Floor |
|----------|-------|
| market | ≥ 3 |
| competition | ≥ 8 |
| ICP / audience | ≥ 6 |
| pricing | ≥ 5 |
| demand | ≥ 12 |

HARDENING-02 must report **per-category funnel**:

```
category: competition
  commercial_blocks: 12
  claims_extracted: 4
  claims_validated: 2
  evidence_accepted: 0
  top_rejection_reasons: [claim_no_category_keyword: 8, no_commercial_domain_overlap: 3]
```

---

## Current vs target code map

| Funnel stage | Current module | HARDENING-02 action |
|--------------|----------------|---------------------|
| Document | `fetch_orchestrator`, `content_extraction` | Replay only — **no changes** |
| DOM blocks | *(missing)* | **Add** `dom_segmentation` |
| Semantic blocks | `content_extraction` (partial) | **Extend** + ledger |
| Commercial blocks | *(missing)* | **Add** `commercial_block_classifier` |
| Claims | `extraction.extract_claims` | **Replace/extend** — block-aware, HTML sentence recovery |
| Validation | `evidence_validation` | Wire per-claim audit |
| Commercial gate | `commercial_relevance` | Tune **extraction-time** signals, not loosen rules |
| Classification | `classification` | Unchanged rules; more input claims |
| Evidence | `skill.py` loop, `evidence_contract` | Instrument; optional batch path |
| Findings | `findings.py`, `finding_traceability` | Unchanged gates |
| Metrics | `pipeline_metrics` | **Add** `claim_funnel` section |
| Validation | `pipeline_validator`, `real_research_readiness` | Add funnel loss alerts |

---

## HARDENING-02 implementation slices (after doc acceptance)

**Order matters. No provider/search edits.**

1. **Contracts** — `BivClaimFunnelMetrics`, `BivClaimAuditEntry`, rejection reason enum
2. **Funnel recorder** — `BivClaimFunnelRecorder` (parallel to `BivPipelineMetricsRecorder`)
3. **DOM segmentation** — block extractor from normalized HTML
4. **Commercial block classifier** — dimension tags + fluff detector
5. **Claim extractor v2** — block-in, claims-out; sentence recovery for HTML; category tagging
6. **Skill integration** — replace inline `extract_claims` loop with funnel stages + audit persistence
7. **Audit API** — operator endpoint `GET .../runs/{id}/claim-funnel` (internal)
8. **Replay script** — re-process run `5eaa7519` fetch ledger bodies offline → funnel report artifact
9. **Regression tests** — golden HTML fixtures; assert stage counts + rejection reasons
10. **Real case re-run** — Marketsynth SaaS; target evidence coverage ≥ 80% **via extraction**, not gate weakening
11. **Owner acceptance** — human audit of 10 accepted + 10 rejected claims with reasons

---

## PASS criteria (HARDENING-02)

Real Marketsynth case must meet **all**:

| Criterion | Threshold |
|-----------|-------------|
| Search success | ≥ 95% (regression — must not regress) |
| Fetch success | ≥ 90% **or** ≥ 35 documents with honest fallback disclosure |
| Documents in funnel | ≥ 35 |
| Claims extracted | ≥ 50 (minimum shape — tune after first replay) |
| Claims validated | ≥ 20 |
| Accepted evidence | ≥ 17 |
| Evidence coverage (floors) | ≥ 80% categories met |
| Category floors | market ≥3, competition ≥8, ICP ≥6, pricing ≥5, demand ≥12 |
| Citation coverage | 100% |
| Unsupported findings | 0 |
| Raw DOM in evidence | 0 |
| Funnel audit | 100% rejected claims have `rejection_reason` |
| Integrity gates | unchanged — zero gate removals |

**Failure response:** report `failed_stage`, metric gap, top-5 rejection reasons per category, retry recommendation. **Never** mark run `succeeded` with empty evidence.

---

## Audit workflow (pre-code)

Before implementation, run **read-only funnel audit** on run `5eaa7519`:

1. Load 40 successful fetch URLs from `biv_fetch_ledger_entries`
2. Re-fetch or use stored normalized text if available
3. Simulate each stage with **current** code + proposed stage counters
4. Produce artifact: `artifacts/real-research-readiness/hardening-02/funnel-audit-5eaa7519.json`
5. Owner reviews loss chart before any production code merge

---

## Explicit prohibitions

| Forbidden | Why |
|-----------|-----|
| Lower evidence floors | Destroys commercial trust |
| Accept tier-D sources as CONFIRMED | Violates classification contract |
| Disable `validate_evidence_acceptance` | Raw DOM / empty URL leakage |
| Skip commercial relevance | Generic macro stats as product viability |
| Mock providers for PASS | HARDENING requires real documents |
| LLM-only claim generation without source anchor | Hallucination path |
| Count search snippets as evidence | Already blocked — keep blocked |

---

## Relationship to HARDENING-01

| HARDENING-01 | Status |
|--------------|--------|
| Fetch ledger | ✅ |
| Pipeline stage metrics | ✅ |
| Fetch fallback contour | ✅ |
| Zero-fetch regression | ✅ |
| Provider preflight w/ direct_http | ✅ |
| Real case execution | ✅ (failed honestly on evidence) |

**HARDENING-01 → `checkpoint_closed`.**  
Program P0 transfers to **HARDENING-02** (this document).

---

## Commercial classification

**Priority A** — core product value: «превращаем интернет в знания».  
Without Evidence Funnel PASS, Marketsynth is a search/fetch demo, not a Business Idea Validator.

**Frozen until HARDENING-02 owner PASS:** QA-01, PRE-LAUNCH implementation, Campaign Plan, Campaign Mode Selector implementation, Ad Format Selector implementation, Yandex Direct Execution.

---

## Cross-references

- [RESEARCH-PIPELINE-HARDENING.md](./RESEARCH-PIPELINE-HARDENING.md) — HARDENING-01 (Fetch/Observability)
- [REAL-RESEARCH-READINESS.md](./REAL-RESEARCH-READINESS.md) — program gate
- `artifacts/real-research-readiness/hardening-01/status.json` — measured baseline
- Run `5eaa7519` fetch ledger — replay input for funnel audit

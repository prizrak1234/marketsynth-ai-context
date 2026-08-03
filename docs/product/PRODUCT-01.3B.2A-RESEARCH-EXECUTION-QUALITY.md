# PRODUCT-01.3B.2A — Research Execution Quality Repair

**Program:** [PRODUCT-FINISH-01](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md) — Step A (repair)  
**Status:** `waiting_for_owner_validation` (second smoke)

---

## Owner FAIL (2026-07-25)

First owner visual smoke **FAIL**: coverage contract visible, research execution commercially useless.

Root defects: mechanical query concatenation, `неизвестно` in search, generic blogger stats as findings, unsupported interim conclusion «перспективной».

**Blocked until repair PASS:** PRODUCT-QA-01, PRODUCT-01.3C.

---

## Repair scope (implemented)

### 1. Query generation (`research_decomposition.py`, `query_strategy.py`)

- Decompose intake into use case, payer, geography, replacement target, pricing hypothesis.
- Strip `unknown` / `неизвестно` from queries; dedupe tokens; never search bare duplicate `SaaS SaaS`.
- Two targeted queries per canonical category (AI/martech/marketing automation framing for SaaS agency case).
- Gap round uses alternate templates (named alternatives, WTP, pricing tiers).

### 2. Research decomposition

- `ResearchIntakeDecomposition.clarification_needed` flags missing payer, use case, alternatives.
- Core search subject built from idea text, not bare product label.

### 3. Evidence-to-finding relevance (`commercial_relevance.py`)

- Reject generic blogger/YouTube economy stats for market/demand/competitors/pricing/risk tracks.
- Audience stats require problem/pain or product linkage.
- Wired in `skill.py` (evidence loop), `findings.py`, `coverage_contract.build_partial_report`.
- Source relevance tightened via decomposed context + commercial domain overlap.

### 4. Unsupported interim conclusion removed

- `build_partial_report` no longer emits «Идея выглядит перспективной» when gate fails.

### 5. Limits

- `MAX_MCP_SEARCH_CALLS` 16, `MAX_MCP_FETCH_CALLS` 18 for multi-query round-1 plan.

---

## Automated regression

```bash
uv run pytest tests/test_product_01_3b_2a_research_execution_quality.py \
  tests/test_product_01_3b_2_research_coverage.py \
  tests/test_product_01_3b_1_gap_presentation.py \
  tests/test_product_01_3b_evidence_integrity.py -q
```

---

## Second owner smoke — PASS criteria (binding scenario unchanged)

Same intake as [PRODUCT-01.3B.2A-OWNER-SMOKE.md](./PRODUCT-01.3B.2A-OWNER-SMOKE.md).

Must observe:

- Queries reflect use case (AI marketing agency), not `SaaS SaaS` / `неизвестно`.
- At least one **commercially relevant** finding each where sources exist: market/demand, competitor/alternative, audience problem.
- Pricing shown as **user hypothesis**, not confirmed market fact.
- At least one commercial risk signal or explicit risk gap.
- **No** unsupported positive conclusion before 01.3C.
- Remediation questions remain concrete.

---

## Owner verdict template

```
PRODUCT-01.3B.2A owner visual smoke (retry): PASS
```

or FAIL with numbered defects.

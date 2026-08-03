# PRODUCT-QA-01 — Commercial Acceptance Harness

**Status:** `blocked` — step **B** of [PRODUCT-FINISH-01](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md)  
**Prerequisite:** Step A — [01.3B.2A owner smoke PASS](./PRODUCT-01.3B.2A-OWNER-SMOKE.md)  
**Type:** Process / quality gate — not a customer-facing product feature  
**Purpose:** Break the cycle «pytest green → browser FAIL → symptom patch → new gap».

---

## Problem (SWOT)

| | |
|--|--|
| **Strength** | Defects caught before external customers |
| **Weakness** | Checks happen too late — after slice marked complete |
| **Risk** | Each patch fixes presentation, not research value |
| **Fix** | Browser acceptance is part of **Definition of Done**, not post-hoc |

---

## Phase status ladder (mandatory)

Cursor must **not** write `COMPLETE` until all four levels pass:

```
implemented
  → automated_verified
  → browser_ready
  → owner_accepted
```

Only **`owner_accepted`** unlocks the next commercial slice.

Allowed Cursor terminal status: **`waiting_for_owner_validation`**.

Forbidden without owner: `accepted`, `frozen`, `commercially ready`, `production ready`.

---

## 1. Golden scenario (BIV)

```
new project
  → confirmed intake
  → research run
  → coverage by track
  → partial findings
  → semantic gaps
  → remediation questions
  → next actions
```

Cursor runs golden scenario **before** calling owner to browser.

Binding fixture: [PRODUCT-01.3B.2A-OWNER-SMOKE.md](./PRODUCT-01.3B.2A-OWNER-SMOKE.md).

---

## 2. Golden fixtures (minimum five)

| Fixture | Expectation |
|---------|-------------|
| Strong idea + good sources | Partial or full findings; coverage mostly confirmed/partial |
| Sparse intake | Honest gaps + concrete questions; no fake verdict |
| Irrelevant sources | Rejected; stop reason explains; no confirmed facts from SEO garbage |
| Provider failure | `provider_failed` on affected tracks only; other tracks continue |
| Conflicting evidence | Contradictions preserved; not collapsed to «insufficient» |

Assert **structure**, not exact copy.

---

## 3. Customer-visible contract tests

Automated guard: UI must never show:

- raw enum / status codes
- hash / internal ID
- raw error code
- raw URL in finding text
- markdown artifacts
- stack trace
- English diagnostic tokens
- Launch Pack without verdict
- confidence without breakdown (when shown)

---

## 4. Browser acceptance (Playwright)

Assert commercial outcome, not just buttons:

- no raw codes in DOM
- partial findings section present when run terminal
- coverage rows present
- user hypotheses labeled
- remediation questions present
- Launch Pack hidden on insufficient

---

## 5. Research quality gate (pre-render)

Chain must be honest:

```
sources found → relevant → independent → classified → evidence → findings
```

If chain breaks at a step → specific failure state, not pseudo-complete report.

---

## 6. Snapshot regression

Per golden scenario store:

- normalized output JSON
- screenshot of result screen

CI compares: required blocks present, forbidden elements absent, structural diff.

---

## 7. Backend ↔ frontend contract

- Backend: structured DTOs only (`category_coverage`, `partial_report`, `semantic_gap_groups`, …).
- Frontend: **never** render raw codes like `coverage_market_insufficient`.
- New enum without Russian customer mapping → **test failure**.

---

## 8. Commercial slice Definition of Done

All required before `owner_accepted`:

- [ ] backend tests green
- [ ] frontend typecheck green
- [ ] E2E green
- [ ] golden scenario green
- [ ] customer-visible contract green
- [ ] **owner browser smoke PASS**

Missing owner PASS → **next slice blocked**.

---

## Recommended queue

| Order | Slice |
|-------|--------|
| **Now** | 01.3B.2A owner visual smoke |
| After PASS | **PRODUCT-QA-01** (this harness) |
| Then | PRODUCT-01.3C Verdict & Confidence Integrity |

---

## Out of scope (QA-01)

- New MCP providers
- Verdict redesign
- Launch Pack / Offer Builder features
- Vector search / Knowledge Core

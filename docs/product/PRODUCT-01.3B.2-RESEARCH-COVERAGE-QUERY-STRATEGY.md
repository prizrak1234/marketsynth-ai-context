# PRODUCT-01.3B.2 — Research Coverage, Query Strategy & Actionable Gaps

**Status:** `waiting_for_owner_validation` — owner browser smoke only; Cursor status frozen here  
**Owner smoke:** [PRODUCT-01.3B.2A-OWNER-SMOKE.md](./PRODUCT-01.3B.2A-OWNER-SMOKE.md)  
**After PASS:** [PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md](./PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md)  
**After FAIL:** open 01.3B.2A Research Execution Quality Repair implementation  
**Blocks:** PRODUCT-01.3C until owner PASS + QA-01 accepted  
**Parent:** PRODUCT-01.3B.1 — presentation corrective **partially accepted**; research value **FAIL**  
**Blocks:** PRODUCT-01.3C–E until owner PASS on 01.3B.2

---

## Owner verdict (2026-07-25)

**PRODUCT-01.3B.1 owner visual smoke: FAIL** — not for raw codes (fixed), but for **commercial research value**.

The screen now correctly shows an honest insufficient-data refusal, but it is **not a market research result**. With adequate intake (SaaS, audience, region, goal, pricing band, stage), the system should run structured research and return **actionable partial findings**, not a long duplicated list of internal gap consequences.

**01.3B presentation slice:** accepted as presentation-only fix.  
**01.3B research-readiness slice:** not accepted until 01.3B.2.

---

## Problem statement

When research runs with usable intake, the product must:

1. Form a research plan aligned to intake (market, competitors, audience, demand, pricing, local context).
2. Execute category-specific queries.
3. Collect multiple independent sources where possible.
4. Separate **confirmed** vs **hypothesis** vs **not found** vs **not researched**.
5. Surface **why** research stopped (connector, quality gate, query breadth, geography).
6. Ask the user **specific** follow-up questions — not generic «уточните контекст / повторите».

Current failures (owner smoke):

- One weak tier-B source treated as insufficient market proof.
- Intake fields (audience, region) not reflected in visible research effort.
- Duplicate gap cards (same root cause repeated 6–10 times).
- Generic remediation («повторите исследование») without concrete intake questions.
- User-provided pricing band not flagged as unverified hypothesis.
- No explanation of **why** fetch/search under-delivered.

---

## Target customer output (even when insufficient)

```
Что удалось установить     — partial findings tied to intake
Что пока не подтверждено   — hypotheses vs missing evidence
Почему исследование остановилось — honest stop reason
Какие данные нужны         — 3–6 specific questions to user
Промежуточный вывод        — actionable hypothesis, not diagnostic codes
```

Not acceptable as final screen:

- Only «данных мало» + duplicated gap list.
- Single irrelevant source presented as research completion.

---

## Mandatory scope (01.3B.2)

### Backend — query & coverage

- Generate **separate research queries** per coverage category: market, competitors, audience, demand, pricing, local context.
- Require **attempt evidence** per critical block (query executed + sources fetched or explicit not_researched).
- Distinguish terminal states:
  - `not_found` — searched, nothing relevant
  - `not_confirmed` — weak/hypothesis only
  - `not_researched` — block skipped
- Do **not** treat one generic source as sufficient for multiple categories.
- Persist and expose **executed queries + coverage plan status** in output DTO (customer-safe summary, not raw MCP dumps).
- **Dedupe** gap codes before presentation (one root cause → one card).
- Map stop reason: connector failure, quality gate, query too broad, geography too vague, etc.

### Backend — intake-aware research

- Bind queries to confirmed intake: audience segments, geography, product type, monetization, stage.
- Flag user-provided pricing as `user_hypothesis` until market-confirmed.
- Minimum: **one relevant source attempt per critical category** before declaring category gap.

### Frontend — actionable report

- Collapse duplicate gaps into 3–4 semantic blocks.
- Show **what was searched** (customer-safe query summary per category).
- Replace generic «повторите» with **specific intake questions** (ICP, use case, competitors, price validation, channel).
- Separate sections: established / unconfirmed / why stopped / what we need / interim conclusion.
- Keep 01.3B.1 rules: no raw codes, no Launch Pack without verdict, no checkboxes on system gaps.

### Out of scope (01.3B.2)

- Verdict & confidence UI polish (**01.3C** — blocked).
- Launch Pack / offer builder.
- New MCP providers or parallel search orchestration beyond existing BIV skill path.

---

## Acceptance criteria (owner visual)

Given intake with product, audience, region, goal, and optional pricing:

1. Screen shows **category coverage** (what was researched vs skipped).
2. At least **attempted** market + competitor + audience queries visible in customer-safe form.
3. Gap list **deduplicated** — no repeated «недостаточно источников» variants.
4. User sees **specific questions** (≥3) tied to missing blocks.
5. Pricing from intake labeled **«указано пользователем, не подтверждено рынком»** when unverified.
6. Stop reason explained in plain Russian.
7. Even on insufficient: **partial findings** when any category has evidence (not one irrelevant card only).
8. No raw diagnostic codes; Launch Pack hidden without verdict.

---

## Regression

```bash
uv run pytest tests/test_product_01_3b_evidence_integrity.py tests/test_product_01_3b_1_gap_presentation.py -q
# + new tests/test_product_01_3b_2_research_coverage.py (to add with slice)
```

---

## Phase queue

| Phase | Status |
|-------|--------|
| 01.3A | accepted (intake-only) |
| 01.3B | FAIL (initial presentation) |
| 01.3B.1 | **partial** — presentation accepted; research value FAIL |
| **01.3B.2** | **OPEN** |
| 01.3C–E | **blocked** |

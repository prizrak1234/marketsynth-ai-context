# PRODUCT-01.3B — Owner Visual Smoke Checklist

**Status:** `FAIL` (initial presentation) → **01.3B.1 partial** (presentation only)  
**Corrective chain:**  
- [01.3B.1](./PRODUCT-01.3B.1-EVIDENCE-GAP-PRESENTATION.md) — presentation **partially accepted**  
- [01.3B.2](./PRODUCT-01.3B.2-RESEARCH-COVERAGE-QUERY-STRATEGY.md) — **OPEN** (research value)  
**Prerequisite:** 01.3A = `conditionally_accepted_as_intake_only`  
**Blocks:** PRODUCT-01.3C — **do not open until 01.3B.2 owner PASS**

---

## Rule

Cursor completes code → **owner visual smoke only** → PASS or defect list → then next slice.

No "Final Report". End state: **Waiting for Owner Validation**.

---

## Pre-flight (Cursor / operator)

- [x] Backend `http://127.0.0.1:8000` — `/health/ready` OK, Alembic `20260724_0060`
- [x] Frontend `http://localhost:3000/workspace`
- [x] PostgreSQL `botfazer_cph1` (not stale SQLite worker)
- [x] API pre-smoke `test_product_01_3b_research_run_api_smoke` — **passed** (~90s, real MCP fetch)
- [ ] **Owner browser visual** — scenarios 1–5 below

### Cursor API pre-smoke (2026-07-24, not a substitute for owner visual)

| Check | Result |
|-------|--------|
| Confirm → no auto-run at API layer | OK (separate research POST) |
| `research_intent` + `biv-research-*` key | OK |
| Run bound to context_id + snapshot_hash | OK |
| Idempotent second run (`lineage_reused`) | OK |
| Hydration scoped to context hash | OK |
| Wrong hash → 404 (no stale report) | OK |
| No Skillbox/YouTube/`To main content` in output blob | OK (API assertion) |
| No raw URLs in evidence claim/observation | OK (API assertion) |

**Owner must still verify UI:** progress, CTA flow, evidence cards layout, relevance by eye.

---

## Scenario 1 — New project, fresh idea (mandatory)

**Idea (never analyzed before):**

> AI-платформа для автоматического создания коммерческих предложений для строительных компаний.

| Step | Action | Expected |
|------|--------|----------|
| 1 | New project | Clean context, no prior report |
| 2 | Enter idea + required intake fields | Form accepts |
| 3 | Confirm context | **No auto-run** — CTA «Начать исследование» visible |
| 4 | Click «Начать исследование» | Real research starts |
| 5 | Observe UI | Progress/stages visible; **not** instant final report |
| 6 | Network | New POST to BIV run with `research_intent`, key `biv-research-*` |
| 7 | Results | No Skillbox/YouTube/stale report from other idea |

**Pass criteria:** research runs, progress shown, no stale instant report.

---

## Scenario 2 — Repeat same idea

| Check | Expected |
|-------|----------|
| Second click «Начать исследование» | Idempotent return of same run OR explicit new run |
| Report content | Same context/hash — **not** foreign report |

---

## Scenario 3 — No garbage in output

After research terminal state, verify **absent**:

- Raw `https://...` in statement body
- `[Skillbox]`, YouTube, «Регистрация ///»
- Markdown artifacts, navigation (`To main content`)

---

## Scenario 4 — Evidence card structure

Each card should show:

- **Источник** (title + domain, not naked URL in statement)
- **Наблюдение** (sanitized text)
- **Почему относится к идее** (relevance / category)
- **Ограничения**

Not: flat link list only.

---

## Scenario 5 — Relevance

For construction CP AI idea, **must not** include:

- Skillbox courses
- Generic SEO articles
- Random YouTube / webinars / ads

---

## Outcome

| Result | Next step |
|--------|-----------|
| **PASS** all scenarios | Owner accepts 01.3B → open 01.3C |
| **FAIL** any scenario | Fix 01.3B only — zero 01.3C code |

---

## Smoke log (fill during run)

| Scenario | Result | Notes |
|----------|--------|-------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

**Owner sign-off:** _______________  
**Date:** _______________

# PRODUCT-01.3 — BIV Intake, Evidence and Report Integrity Repair

**Status:** `open` — **01.3A implemented** (smoke pending); **01.3B chartered**; 01.3C–D pending  
**Priority:** P0 (commercial honesty)  
**Depends on:** CMVP.1 / BIV runtime (existing)  
**Blocks:** PRODUCT-01 freeze, PRODUCT-00.5 audit, PRODUCT-MEDIA-01

---

## Objective

Restore commercial honesty on the path **Idea → Research → Verdict** so that:

1. No analysis runs without **confirmed** project context.
2. Hydrated history requires **explicit user confirmation**.
3. Customer report contains **no raw search snippets** as confirmed findings.
4. Verdict and confidence are **earned**, not decorative.
5. Stage progress reflects **real artifacts**, not timers.

Offer Builder (PRODUCT-01 runtime) is **out of scope** for this slice except regression tests proving blocked Launch Pack when BIV is invalid.

---

## Owner rejection evidence (2026-07-24)

Observed on live `/workspace` click-through:

- Generic prefilled idea analyzed without user confirmation
- «Подтверждённые выводы» contained support-line boilerplate, scraped markdown, URLs
- Verdict «Запуск целесообразен» with 87% confidence without visible substantiation
- All analysis stages green without readable section outputs

---

## Required user journey (target)

```
1. User clicks «Проверить идею»
2. System shows:
   - current saved idea (if any), OR
   - empty intake form
3. User chooses:
   - continue with saved context (explicit confirm)
   - edit description
   - start new project
4. System shows missing fields + clarifying questions
5. User confirms intake
6. Analysis runs
7. Structured report sections render
8. Verdict only if gates pass
```

### Minimum intake fields (collect or confirm)

- What we sell
- Target customer
- Geography / market
- Business model
- Price range (optional)
- Project stage
- Budget (optional)
- Known competitors (optional)
- Validation goal

---

## Report structure (target)

| Section | Must show |
|---------|-----------|
| Исходные данные | Known / assumed / missing |
| Рынок | Evidence + source limitations |
| Целевая аудитория | Segments, problems, unknowns |
| Конкуренты | Who found, gaps |
| Экономика | Known params, assumptions, incalculable |
| Риски | Critical, manageable, information gaps |
| Вердict | Rationale, conditions, next step |

**Forbidden in customer UI:** raw markdown links, `[To main content]`, concatenated scrape text, search snippets labeled «подтверждено».

---

## Implementation priorities (ordered)

### P0 — Intake gate ✅ PRODUCT-01.3A

See [PRODUCT-01.3A-INTAKE-HYDRATION-CONSENT.md](./PRODUCT-01.3A-INTAKE-HYDRATION-CONSENT.md)

| ID | Fix | Status |
|----|-----|--------|
| 01.3-A1 | Block run until intake confirmed | ✅ |
| 01.3-A2 | Hydration consent card | ✅ |
| 01.3-A3 | Backend specificity gate | ✅ |
| 01.3-A4 | Extended intake fields | ✅ |

### P0 — Evidence integrity

| ID | Fix | Area |
|----|-----|------|
| 01.3-B1 | Fix `audience_has_support()` — hypothesis segments must not satisfy gate | `audience_segmentation.py` |
| 01.3-B2 | Split findings: confirmed vs hypothesis in UI; honor `is_hypothesis` | `business-validation-result-card.tsx`, TS types |
| 01.3-B3 | Harden claim extraction: reject nav boilerplate, markdown artifacts, URL-only claims | `extraction.py`, `sanitize_external_text` |
| 01.3-B4 | Link each finding to evidence IDs + source title in UI | result card |
| 01.3-B5 | Do not auto-label search snippets as confirmed | `findings.py`, `skill.py` |

### P0 — Verdict & confidence honesty

| ID | Fix | Area |
|----|-----|------|
| 01.3-C1 | Hide or replace raw % when gate failed / insufficient evidence | `business-validation-result-card.tsx` |
| 01.3-C2 | Show confidence breakdown (coverage, unknowns, contradictions) | result card + `BusinessIdeaValidationConfidence` |
| 01.3-C3 | Block `proceed` verdict when idea specificity gate fails | `verdict_mapper.py`, coverage gate |

### P1 — Stage progress honesty

| ID | Fix | Area |
|----|-----|------|
| 01.3-D1 | Remove cosmetic 420ms timer-all-green | `agency-analysis-flow.ts` |
| 01.3-D2 | Stage ✓ only when backend stage artifact valid | map from `coverage_plan` / skill stages |
| 01.3-D3 | Show partial progress when categories missing | `agency-analysis-stages.tsx` |

### P1 — Rendering

| ID | Fix | Area |
|----|-----|------|
| 01.3-E1 | Strip markdown link syntax from customer-facing statements | sanitization + render |
| 01.3-E2 | Normalize whitespace / concatenation bugs | extraction + display |

---

## Tests (required)

| Test | Assertion |
|------|-----------|
| New user, no input, clicks validate | No verdict; intake required |
| Hydrated project on load | Confirmation required before re-run |
| Snippet-only fetch body | No confirmed finding |
| Generic prefilled idea | `insufficient_evidence` or intake block |
| Gate fail | No decorative 87%; no «Запуск целесообразен» |
| Finding with `is_hypothesis=true` | Not under «Подтверждённые выводы» |

Existing: `tests/test_cmvp_1_business_idea_validation.py` — extend, do not replace.

---

## Hard boundaries (this slice)

**Forbidden:**

- Offer Builder changes (except blocked-path regression)
- Launch Pack / PRODUCT-MEDIA-01
- Content Strategy / Copywriting
- Higgsfield
- Lowering coverage gates to fake green verdicts

**Allowed:**

- BIV intake UX
- Evidence / findings / verdict honesty
- Report rendering
- Tests + docs

---

## Definition of done

1. Owner re-runs click-through: describes idea → confirms intake → sees structured honest report
2. No raw scrape text in «Подтверждённые выводы»
3. Verdict matches evidence state
4. Hydration requires confirmation
5. Tests green
6. PRODUCT-01.2 re-acceptance attempted (Postgres + E2E + browser)

---

## Code map (current defects)

| Defect | Primary files |
|--------|---------------|
| Immediate run on card click | `intent-start-panel.tsx`, `workspace-home-view.tsx` |
| Silent hydration | `workspace-home-view.tsx` `hydrateFromProject()` |
| «Подтверждённые выводы» mislabel | `ru.ts`, `business-validation-result-card.tsx` |
| Auto-accept evidence | `skill.py` `_create_accepted_evidence()` |
| Audience gate bug | `audience_segmentation.py` `audience_has_support()` |
| Cosmetic stages | `agency-analysis-flow.ts`, `agency-analysis-stages.tsx` |
| Confidence display | `business-validation-result-card.tsx`, `confidence.py` |

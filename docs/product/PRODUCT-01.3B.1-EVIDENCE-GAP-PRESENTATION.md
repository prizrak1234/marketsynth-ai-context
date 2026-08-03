# PRODUCT-01.3B.1 — Evidence Gap Presentation & Customer-Safe Report

**Status:** `partially_accepted_presentation_only` — owner smoke **FAIL** on research value (2026-07-25)  
**Presentation:** PASS — no raw codes, honest insufficient UI  
**Research value:** FAIL — diagnostic refusal, not actionable research output  
**Next:** [PRODUCT-01.3B.2-RESEARCH-COVERAGE-QUERY-STRATEGY.md](./PRODUCT-01.3B.2-RESEARCH-COVERAGE-QUERY-STRATEGY.md)  
**Blocks:** PRODUCT-01.3C–E until **01.3B.2** owner PASS

## Problem (01.3B FAIL)

Customer UI showed raw backend diagnostic codes (`fewer_than_3_fetched_sources`, `business_verdict_missing`, etc.) instead of Russian customer-facing explanations. Launch Pack was advertised without a valid business verdict. Research was labeled "completed" while stages were incomplete.

## Corrective scope

| Layer | Change |
|-------|--------|
| Backend | `gap_presentation.py` — translation map for all gap codes → `BivResearchGapPresentation` |
| Backend | `skill.py` — populate `research_gap_items`; fix `business_verdict_id` ordering |
| Backend | `decision_branch.py` — no raw codes in explanation/conditions; Launch Pack blocked for insufficient |
| Frontend | `business-validation-result-card.tsx` — honest insufficient state, gap info cards, no raw codes |
| Frontend | `research-gap-presentation.ts` — customer helpers, Launch Pack gate |
| Frontend | `agency-analysis-flow.ts` — `insufficient_evidence` status, stages only task done |
| Frontend | `workspace-home-view.tsx` — hide Launch Pack until valid verdict; refine/retry actions |
| Frontend | `agency-result-actions.tsx` — Уточнить данные / Повторить исследование |

## Owner re-smoke checklist

1. Run research on confirmed intake with sparse context (expect insufficient evidence).
2. **Must NOT see** raw codes in any customer block.
3. Title: «Данных недостаточно…» or «Исследование не собрало…» — not «Структурированные доказательства готовы».
4. Gap items are informational cards — **no checkboxes**.
5. Stages: only «Изучаем задачу» done; status «Исследование остановлено…».
6. **No Launch Pack** panel when `business_verdict_id` is null / insufficient.
7. Actions: «Уточнить данные» → intake with field focus; «Повторить исследование» → new run.

## Regression

```bash
uv run pytest tests/test_product_01_3b_1_gap_presentation.py tests/test_product_01_3b_evidence_integrity.py -q
```

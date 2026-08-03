# PRODUCT-01.3A.3 — Specificity Gate UX Repair

**Status:** implemented (awaiting owner re-smoke)  
**Blocks:** PRODUCT-01.3B until 01.3A smoke PASS

## Problem (re-smoke FAIL)

Intake form loaded but **Confirm** stayed disabled: `missing_fields` was stale after edits, optional fields were not in the form, and the validation alert had poor dark-theme contrast.

## Fix (Variant B)

**Blocking (minimum gate):** idea, product, audience OR unknown, geography OR unknown, goal.

**Non-blocking:** pricing, competitors, stage, budget → `research_gap_*` warnings only.

## Changes

| Area | Change |
|------|--------|
| `analysis_context_gate.py` | `BLOCKING_FIELDS`, optional research-gap warnings |
| `analysis-context-specificity.ts` | Client-side gate mirror + live recompute |
| `workspace-home-view.tsx` | Recompute `missing_fields` on every edit |
| `analysis-intake-panel.tsx` | Optional fields, readable alert, clickable missing links |
| i18n `ru` / `en` | New intake copy |
| Tests | `test_product_01_3a_3_specificity_gate_ux.py`, e2e extensions |

## Owner re-smoke

1. Open `/workspace` → «Проверить идею»
2. Fill product, audience, geography, goal (idea pre-filled)
3. Confirm button **enabled**
4. Optional section: mark pricing/competitors «Пока неизвестно» → still enabled, research gaps notice shown
5. Confirm → analysis starts only after confirm

## Regression

```powershell
uv run pytest tests/test_product_01_3a_3_specificity_gate_ux.py tests/test_product_01_3a_biv_intake_gate.py -q
cd web && npm run typecheck
```

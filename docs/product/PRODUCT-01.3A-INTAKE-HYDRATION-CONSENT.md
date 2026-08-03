# PRODUCT-01.3A — Intake & Hydration Consent Gate

**Status:** `implemented` — **owner smoke pending** ([smoke protocol](./PRODUCT-01.3A-SMOKE-PROTOCOL.md))  
**Do not:** full PRODUCT-01.3E or Offer path until 01.3B–D complete

---

## Objective

Block Business Idea Validation until the user explicitly confirms what is being analyzed.

No silent hydration. No auto-run on intent card click. No progress UI before a backend run exists.

---

## Delivered

### Backend

- `analysis_contexts` table + Alembic `20260724_0060`
- `AnalysisContextService` — draft, confirm, edit, start-new, get current
- API under `/projects/{project_id}/analysis-contexts/*`
- BIV run requires `analysis_context_id` + `input_snapshot_hash`
- Specificity gate in `analysis_context_gate.py`
- BIV runs bind `analysis_context_id` + hash

### Frontend

- `HydrationRecoveryCard` — continue / edit / start new
- `AnalysisIntakePanel` — confirm before run
- `workspace-home-view.tsx` — no auto-verdict on mount; no auto-run on card click
- Stages only during `analyzing` phase

### Tests

- `tests/test_product_01_3a_biv_intake_gate.py` (23 cases)

---

## Out of scope (01.3B–D)

- Evidence sanitization
- Verdict/confidence honesty
- Report rendering repair
- Honest stage artifacts

---

## Verification

```bash
uv run pytest tests/test_product_01_3a_biv_intake_gate.py -q
cd web && npm run typecheck
```

Owner browser check:

1. Open `/workspace` with saved project → recovery card, no verdict
2. Click «Проверить идею» → intake form, no analysis
3. Confirm → analysis starts
4. «Начать новый проект» → empty form, history preserved

---

## Next slice

**PRODUCT-01.3B** — Evidence Integrity & Source Sanitization

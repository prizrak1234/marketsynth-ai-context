# PRODUCT-01.3A.4 — Browser-Only Owner Smoke Preparation

**Date:** 2026-07-24  
**PRODUCT-01.3A.status:** `conditionally_accepted_as_intake_only`  
**Next slice:** PRODUCT-01.3B (Evidence Integrity + real research run)

---

## Stack status (Cursor-prepared)

| Check | Status |
|-------|--------|
| Backend `:8000` | Running — `analysis_context_subsystem.ready=true` |
| Frontend `:3000` | Running — HTTP 200 `/workspace` |
| PostgreSQL Alembic | `20260724_0060` (head) |
| OpenAPI analysis-context routes | 5 paths present |
| Frontend → backend | `http://127.0.0.1:8000` (loopback-aligned) |

**Browser opened:** [http://localhost:3000/workspace](http://localhost:3000/workspace)

No terminal action required from owner.

---

## Automated pre-smoke (all green)

| Suite | Result |
|-------|--------|
| `test_product_01_3a_biv_intake_gate.py` | 24 passed |
| `test_product_01_3a_3_specificity_gate_ux.py` | 6 passed |
| `test_product_01_3a_backend_availability.py` | 3 passed |
| Frontend `npm run typecheck` | pass |
| Scoped ruff (01.3A files) | pass |

E2E (`product-01-3a-intake-smoke.spec.ts`) requires pilot credentials — run in CI/owner session when creds available.

---

## Owner decision record (prior visual smoke)

### Intake gate — PASS

- Form opens after «Проверить идею»
- User input confirmed before analysis
- No auto-verdict / no auto-run before confirmation
- Specificity gate UX (01.3A.3) unblocks confirm button

### Full downstream — FAIL (expected; out of 01.3A scope)

- Irrelevant report vs submitted idea
- Raw search/snippet garbage in «Подтверждённые выводы»
- Markdown/URLs/navigation in customer UI
- Confidence % conflicts with insufficient evidence
- Final report visible while stages incomplete
- «Начать исследование» not bound to real research run

**Decision:** Accept **01.3A as intake-only**. Open **01.3B** immediately. Do not re-smoke broken report for 01.3A PASS.

---

## Owner visual checklist (browser only)

Use only if re-validating intake after a patch. **Do not judge report quality here** — that is 01.3B.

1. Open `/workspace` (log in if prompted).
2. Click «Проверить идею».
3. Intake form visible — no «Not Found» / «Сервис недоступен».
4. Fill: idea, product, audience, geography, goal.
5. «Подтвердить и продолжить» becomes **active**.
6. Optional: mark pricing/competitors «Пока неизвестно» — button stays active.
7. Click confirm — analysis starts **only after** click.
8. No green stages before confirmation.
9. Reload — intake state restores sensibly.
10. «Изменить описание» — reconfirmation required.
11. «Начать новый проект» — form clears; history remains.

**Intake PASS criteria:** steps 1–8 + 10–11. Step 9 optional sanity check.

**Do not FAIL 01.3A** for report garbage, wrong competitors, or fake confidence — log under 01.3B/01.3C.

---

## Status rule

| Phase | Status |
|-------|--------|
| PRODUCT-01.3A intake | `conditionally_accepted_as_intake_only` |
| PRODUCT-01.3A full E2E | blocked on 01.3B–D |
| PRODUCT-01.3B | **open** — next implementation slice |

After 01.3B owner acceptance → 01.3C → 01.3D → 01.3E full acceptance.

---

## Fail handling (owner reports intake FAIL)

Owner sends: screenshot + step number + short note.  
Cursor reproduces, collects logs/Network internally, patches 01.3A only, reruns automated checks, reopens browser. Owner is not asked to use terminal.

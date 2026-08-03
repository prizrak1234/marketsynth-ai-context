# PRODUCT-01.3A — Owner Smoke Protocol

**Purpose:** Narrow browser verification of intake gate only.  
**Not:** full path to Offer, verdict quality, or report honesty (known broken in 01.3B–D).

**When:** Before opening PRODUCT-01.3B code.  
**Who:** Owner (or delegate with pilot credentials).

---

## Preconditions

- Backend running with migration `20260724_0060` applied
- Logged-in pilot user
- Optional: existing project with prior BIV data (for recovery card)

---

## Smoke checklist (10 steps)

| # | Action | Pass criteria |
|---|--------|---------------|
| 1 | Open `/workspace` | Page loads; no API unavailable block |
| 2 | Observe initial state | **Old verdict does NOT appear automatically** |
| 3 | If saved data exists | **Recovery card** visible: «Найдены сохранённые данные проекта» |
| 4 | Click «Продолжить с этими данными» | Moves toward confirm; **does not start analysis alone** if fields incomplete |
| 5 | Complete / confirm intake | Explicit confirmation required before run |
| 6 | Click «Изменить описание» | Form editable; prior confirm invalidated |
| 7 | Edit + confirm again | Re-confirmation required; analysis only after second confirm |
| 8 | Click «Начать новый проект» | Empty intake; **historical projects/reports still exist** in history |
| 9 | Before any confirm | **No analysis running**; **no green stage checkmarks** |
| 10 | After confirm + run | Analysis may start; stages appear only during run |

---

## Explicit non-checks (defer to 01.3E)

- «Подтверждённые выводы» content quality
- Confidence % honesty
- Verdict «Запуск целесообразен» justification
- Offer / Launch Pack path
- Markdown/URL garbage in report body

---

## Outcome

| Result | Next step |
|--------|-----------|
| **All 10 pass** | Mark 01.3A **technically accepted** → open **PRODUCT-01.3B** |
| **Any fail** | Fix 01.3A only; do not start 01.3B |

Record outcome in this file:

```
Smoke date:
Tester:
Result: pass | fail
Notes:
```

---

## Automated backing (already green)

```bash
uv run pytest tests/test_product_01_3a_biv_intake_gate.py -q
cd web && npm run typecheck
```

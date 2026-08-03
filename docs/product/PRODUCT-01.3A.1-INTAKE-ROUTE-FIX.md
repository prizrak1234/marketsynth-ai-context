# PRODUCT-01.3A.1 — Intake Route & UX Corrective Patch

**Status:** `implemented` — re-smoke pending  
**Trigger:** PRODUCT-01.3A smoke FAIL — «Not Found» on «Проверить идею», intake form not opening

---

## Root cause (likely)

1. **FastAPI route 404** — backend running stale build without `analysis-contexts` router and/or migration `20260724_0060` not applied
2. **Stale `project_id`** — frontend reused invalid project; API returned tenant-safe 404
3. **Error envelope mismatch** — API returns `{ error_code, safe_message }` but client showed raw `Not Found` from FastAPI default

---

## Fixes applied

### Frontend

- **Optimistic intake UI** — form opens immediately on BIV intent click; backend sync async
- **`createAnalysisContextDraftResilient`** — retry with fresh project on 404
- **`ensureProjectId`** — validates project via `GET /projects/{id}` before reuse
- **`loadAnalysisContext`** — skips stale projects in list
- **`extractApiErrorInfo`** — customer-safe messages; no raw «Not Found»
- **Local draft fallback** — form stays visible if API fails (with friendly error)

### Backend tests

- `test_api_analysis_context_routes_registered` — OpenAPI + GET current returns 200

### E2E

- `web/e2e/product-01-3a-intake-smoke.spec.ts`

---

## Owner re-smoke checklist

Same 10 steps as [PRODUCT-01.3A-SMOKE-PROTOCOL.md](./PRODUCT-01.3A-SMOKE-PROTOCOL.md)

**Before smoke:**

```bash
uv run alembic upgrade head   # must include 20260724_0060
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd web && npm run dev -- --port 3000
```

Verify `/docs` lists analysis-context routes.

---

## Gate

- **PASS** → 01.3A technically accepted → open 01.3B
- **FAIL** → fix 01.3A.1.x only; no 01.3B

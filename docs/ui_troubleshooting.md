# BotFazer ops UI — Troubleshooting

Quick fixes for **internal demo** setup. For step-by-step verification use [ui_demo_smoke_checklist.md](./ui_demo_smoke_checklist.md).

---

## Symptom index

| Symptom | Jump to |
|---------|---------|
| Blank page / “Set API key” | [Config](#config-missing-in-ui) |
| All API calls fail / 401 | [Auth](#401-unauthorized) |
| Empty campaigns / wrong data | [Project scope](#wrong-or-empty-project-data) |
| Seed script fails | [Seed](#demo-seed-fails) |
| CORS error in browser | [CORS](#cors--network) |
| Schedule rejected | [Scheduling](#schedule--reschedule-errors) |
| Generate assets error | [Plan draft](#plan-draft-generate-assets) |
| Metrics look stale | [Cache](#stale-ui-after-actions) |
| Telegram not sending | [Telegram](#telegram-not-sending-not-a-ui-bug) |

---

## Config missing in UI

**Panels:** “Set `NEXT_PUBLIC_BOTFAZER_API_KEY`” or “Set `NEXT_PUBLIC_BOTFAZER_PROJECT_ID`”.

**Fix:**

1. Create `web/.env.local` from `web/.env.example`.
2. Run seed and copy **all three** lines:
   ```powershell
   uv run python scripts/seed_demo_marketing_flow.py --refresh-api-key
   ```
3. **Restart** `npm run dev` (Next.js reads env at startup).

**Check:** Browser devtools → no requests without `Authorization: Bearer bfz_...`.

---

## 401 Unauthorized

| Cause | Fix |
|-------|-----|
| Wrong or expired API key | Re-seed with `--refresh-api-key`, update `.env.local`, restart web |
| Key not passed | Ensure variable name is `NEXT_PUBLIC_BOTFAZER_API_KEY` (not server-only `BOTFAZER_API_KEY`) |
| API not running | `curl http://127.0.0.1:8000/health` |

---

## Wrong or empty project data

| Cause | Fix |
|-------|-----|
| `PROJECT_ID` from another seed run | Re-run seed, paste **new** project id from stdout |
| Campaign filters | On `/campaigns`, set status filter to **All**, check “include archived” |
| Different database than seed | Same `DATABASE_URL` for API and seed; for sqlite use one file path |

---

## Demo seed fails

| Error | Fix |
|-------|-----|
| `Demo API key already exists` | Add `--refresh-api-key` |
| `no such column` / schema errors | SQLite drift: `--reset-db` with explicit file: `$env:DATABASE_URL="sqlite+aiosqlite:///./botfazer.db"` |
| `PermissionError` on delete | Stop API using the db file, then re-run seed |
| Migration errors on Postgres | `uv run alembic upgrade head` then seed **without** `--reset-db` on production DB |

**Success looks like:** stdout ends with `NEXT_PUBLIC_BOTFAZER_PROJECT_ID=...` and `API_KEY=bfz_...`.

---

## CORS / network

**Symptom:** Browser console: CORS blocked on `http://127.0.0.1:8000`.

**Fix:**

- API `APP_ENV=development` (allows `http://localhost:3000`).
- `NEXT_PUBLIC_BOTFAZER_API_BASE_URL` must match running API (no trailing slash).
- UI on `localhost:3000`, API on `127.0.0.1:8000` — usually OK in dev; if not, align hostnames.

**Symptom:** `Failed to fetch` / connection refused.

**Fix:** Start API first; confirm port 8000 free.

---

## Schedule / reschedule errors

| Message | Meaning |
|---------|---------|
| Client: “Scheduled time must be in the future” | Pick later `datetime-local` |
| 422 on `scheduled_at` | Naive datetime or past UTC — use UI form, not raw past ISO |
| 409 asset not approved | Only **approved** assets; approve in review first |
| No channels in dropdown | Create channel at `/settings/channels`; status **active** |
| 409 channel not active | Activate channel in channels table |

**API:** `POST /projects/{project_id}/publication-jobs`  
**Reschedule:** `POST .../publication-jobs/{id}/reschedule`

---

## Plan draft generate assets

| Error | Fix |
|-------|-----|
| `plan_draft_generation_partial_state` | Partial assets exist; archive plan or fix via API; do not click generate repeatedly expecting fix |
| Archived campaign / plan | Read-only — use active campaign |
| No content items | Plan must have ≥1 item in form |

**API:** `POST .../plan-drafts/{id}/generate-assets`

---

## Stale UI after actions

**Symptom:** Approved asset still in review queue until refresh.

**Try:**

1. Hard refresh page.
2. If persists, note for bug report (invalidation); include campaign id and action taken.

**Workaround:** Navigate away and back to `/review` or `/campaigns/{id}`.

---

## Telegram not sending (not a UI bug)

Scheduling in UI creates a **scheduled** job row. Actual Telegram delivery requires:

- `TELEGRAM_PUBLICATION_BOT_TOKEN` on API server
- `TELEGRAM_PUBLICATION_ENABLED=true` (if used)
- Publication worker / processor running

**UI demo success** = job visible in **Publication calendar** with status `scheduled` (or `cancelled` after cancel test).

---

## Lint / build (maintainers)

```powershell
cd web
npm run lint
npm run build
```

Type errors often trace to API type drift in `web/src/lib/api/types/`.

---

## When to escalate

Open an issue with:

1. Git commit hash  
2. `web/.env.local` **keys only** (never paste API key value)  
3. Screenshot + network tab status code for failed request  
4. Filled row from [ui_tester_feedback_template.md](./ui_tester_feedback_template.md)  

---

## Related docs

- [ui_demo_script.md](./ui_demo_script.md) — live demo narrative  
- [ui_demo_readiness_audit.md](./ui_demo_readiness_audit.md) — known limitations  
- [ui_invariants.md](./ui_invariants.md) — expected behavior  

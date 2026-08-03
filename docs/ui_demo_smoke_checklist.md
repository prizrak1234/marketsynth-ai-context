# UI demo smoke checklist (Phase UI.11)

Manual end-to-end walkthrough for the **Internal Operations UI** (`web/`). Goal: confirm the product is demonstrable **without Swagger**.

## Prerequisites

| Item | Notes |
|------|--------|
| API running | `uv run uvicorn app.main:app --reload` (repo root) |
| Demo data | See [Seed demo](#1-seed-demo) |
| Web env | `web/.env.local` with `NEXT_PUBLIC_BOTFAZER_*` from seed output |
| Web dev server | `cd web && npm run dev` → http://localhost:3000 |

**Automated sanity (before manual pass):**

```powershell
uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key
cd web
npm run lint
npm run build
```

---

## Demo path

### 1. Seed demo

| | |
|---|---|
| **Action** | From repo root: `uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key` (sqlite dev) or seed without `--reset-db` if DB already migrated. |
| **Expected** | Script completes; prints `NEXT_PUBLIC_BOTFAZER_PROJECT_ID` and `NEXT_PUBLIC_BOTFAZER_API_KEY`; creates user, project **Demo Marketing Project**, campaign **Q2 Launch Demo**, Telegram channel, plan draft, 3 draft assets, 1 approved asset, 1 pending review draft, 1 scheduled job. |
| **Common failure** | `Demo API key already exists` → add `--refresh-api-key`. Stale sqlite schema → `--reset-db` with `DATABASE_URL=sqlite+aiosqlite:///./botfazer.db`. API not running does not affect seed (DB-only). |
| **API** | _(services only — no HTTP)_ |

---

### 2. Open Dashboard

| | |
|---|---|
| **Action** | Open `/` with valid `.env.local`. |
| **Expected** | Health line in header when API up; metric cards load (campaigns, pending review ≥ 1 after seed, scheduled publications ≥ 1). Numbers reflect **scoped project** when `NEXT_PUBLIC_BOTFAZER_PROJECT_ID` is set. |
| **Common failure** | “Set API key” / “Set project ID” panels → fix `.env.local`. All metrics `—` or error panel → API down or wrong key. |
| **API** | `GET /health`, `GET /projects/{project_id}/operational-metrics` (or `GET /me/operational-metrics` if no project id) |

---

### 3. Open Campaigns

| | |
|---|---|
| **Action** | Sidebar → **Campaigns** (`/campaigns`). |
| **Expected** | Table lists **Q2 Launch Demo** (active); workflow badge; pending review count ≥ 1; optional next publication time. |
| **Common failure** | Empty list → wrong `PROJECT_ID` or filters hiding campaign. Spinner stuck → API/auth. |
| **API** | `GET /projects/{project_id}/campaigns`, per row: `GET .../campaigns/{id}/workflow`, `GET .../campaigns/{id}/overview` |

---

### 4. Open campaign

| | |
|---|---|
| **Action** | Click campaign title → `/campaigns/{id}`. |
| **Expected** | Overview (status badge, asset counts, jobs, next publication); workflow state badge; plan drafts section; publication calendar; campaign assets with links to `/assets/{id}`. |
| **Common failure** | 404/error panel → wrong id or project scope. Overview/workflow mismatch → refresh page (cache). |
| **API** | `GET .../campaigns/{id}/overview`, `GET .../workflow`, `GET .../plan-drafts`, `GET .../publication-jobs`, `GET .../assets` |

---

### 5. Create plan draft

| | |
|---|---|
| **Action** | On campaign page: **Create plan draft** (or expand form), fill title + at least one content item, submit. _(Seed already has **Demo launch plan** — optional for repeat demo.)_ |
| **Expected** | Toast “Plan draft created”; draft appears in table; detail panel can open. |
| **Common failure** | Validation toast (empty title/items). Archived campaign → read-only message, no form. |
| **API** | `POST .../campaigns/{id}/plan-drafts` |

---

### 6. Generate assets

| | |
|---|---|
| **Action** | Open plan draft → **Generate draft assets**. |
| **Expected** | Toast with `created_count` or `already_generated`; review queue gains draft assets; campaign asset list updates. Link hint to review queue in plan panel. |
| **Common failure** | `plan_draft_generation_partial_state` → partial assets; archive plan and recreate. Archived plan → button hidden. |
| **API** | `POST .../plan-drafts/{draft_id}/generate-assets` |

---

### 7. Open Review Queue

| | |
|---|---|
| **Action** | Sidebar → **Review Queue** (`/review`). |
| **Expected** | Table of draft assets; **Open** / **Approve** / **Archive**; asset title links to editor. |
| **Common failure** | “No pending review” → all approved/archived; run generate or seed again. |
| **API** | `GET /projects/{project_id}/review-queue` |

---

### 8. Approve pending asset

| | |
|---|---|
| **Action** | On a **draft** row → **Approve** (not the one already approved in seed if demonstrating twice). |
| **Expected** | Toast success; row disappears from queue; campaign workflow/overview counts update when returning to campaign. |
| **Common failure** | 409 → asset not draft. No UI change → check invalidation / wrong project. |
| **API** | `POST /projects/{project_id}/content-assets/{asset_id}/approve` |

---

### 9. Open Asset

| | |
|---|---|
| **Action** | **Open** from review or click asset under campaign → `/assets/{id}`. |
| **Expected** | Draft: edit title/body + **Create revision**. Approved: schedule form + create revision from approved. Version history + preview. Approve/Archive in header when applicable. |
| **Common failure** | Config missing panels. Schedule hidden on draft (by design). |
| **API** | `GET .../content-assets/{id}`, `GET .../versions`, `GET .../versions/{n}` |

---

### 10. Schedule publication

| | |
|---|---|
| **Action** | On **approved** asset → **Schedule publication** → pick channel + future local time → **Submit schedule**. |
| **Expected** | Toast “Publication scheduled”; job appears on campaign **Publication calendar** with status `scheduled`. |
| **Common failure** | No channels → create at `/settings/channels`. Past time → client or 422 error message. Non-approved asset → form not shown. |
| **API** | `GET .../publishing-channels`, `POST /projects/{project_id}/publication-jobs` |

---

### 11. Open Campaign Calendar

| | |
|---|---|
| **Action** | Campaign detail → **Publication calendar** section (same page as step 4). |
| **Expected** | Jobs grouped by status; **scheduled** rows show Reschedule / Cancel; asset title links to `/assets/{id}`; times formatted locally. |
| **Common failure** | Empty state → no jobs yet; schedule from asset page. Only non-scheduled statuses → expand groups (queued, cancelled, etc.). |
| **API** | `GET .../campaigns/{id}/publication-jobs` |

---

### 12. Reschedule job

| | |
|---|---|
| **Action** | On a **scheduled** job → **Reschedule** → new future time → **Save new time**. |
| **Expected** | Toast “Publication rescheduled”; displayed time updates; status stays `scheduled`. |
| **Common failure** | Past time → error toast. 409 → job no longer scheduled (refresh). |
| **API** | `POST /projects/{project_id}/publication-jobs/{job_id}/reschedule` |

---

### 13. Cancel job

| | |
|---|---|
| **Action** | **Cancel** → confirm dialog → **Cancel job**. |
| **Expected** | Toast success; job moves to **cancelled** group (or disappears from scheduled). |
| **Common failure** | 409 if already queued/running. |
| **API** | `POST /projects/{project_id}/publication-jobs/{job_id}/cancel` |

---

### 14. Check Channels page

| | |
|---|---|
| **Action** | Sidebar → **Channels** (`/settings/channels`). |
| **Expected** | **Demo Telegram** listed; create form works; Activate/Pause/Archive on non-archived channels. |
| **Common failure** | Empty → seed not run or wrong project. Create validation errors on missing `chat_id`. |
| **API** | `GET/POST/PATCH/DELETE .../publishing-channels` |

---

### 15. AI chain demo (Marketer multi-subagent)

| | |
|---|---|
| **Prerequisites** | Backend `.env`: `AGENT_CHAT_TOOLS_ENABLED=true`, `TOOLS_PROVIDER_ENABLED=true` (and write flags if demonstrating plan draft / revision). Seed creates **orchestrator**, **researcher**, **strategist**, **copywriter** (active). API + `npm run dev` running. |
| **Action** | Sidebar → **AI Chat** (`/agents/chat`). Select campaign **Q2 Launch Demo**. Agent = **orchestrator**. Send: `Запусти новый продукт в Telegram`. |
| **Expected** | Panel **Handled by** with summary `Researcher → Strategist → Copywriter`. Three steps: subagent name, `succeeded` status, short run id, **Run details** link per step. No approve / schedule / publish buttons in chat. Assistant reply from final (copywriter) step only. |
| **Common failure** | Single sub-agent only → wrong agent selected (not orchestrator). Empty chain → missing researcher/strategist/copywriter agents in project. 503 → API tools/LLM unavailable. |
| **API** | `POST .../agent-chat` → `subagent_chain[]` with `{ subagent, agent_run_id, status }`; `GET /agent-runs/{id}` for run details page |

**Automated smoke:**

```bash
uv run pytest tests/test_subagent_chain_execution.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
uv run pytest tests/test_phase_ai_14_2_chain_demo_smoke.py
```

---

## Post-walk notes (fill when testing)

| Step | Pass? | Issues found |
|------|-------|----------------|
| 1 Seed | | |
| 2 Dashboard | | |
| 3 Campaigns | | |
| 4 Campaign detail | | |
| 5 Create plan | | |
| 6 Generate | | |
| 7 Review | | |
| 8 Approve | | |
| 9 Asset | | |
| 10 Schedule | | |
| 11 Calendar | | |
| 12 Reschedule | | |
| 13 Cancel | | |
| 14 Channels | | |
| 15 AI chain | | |

## Out of scope (do not test as product gaps)

- Login / auth UI
- Swagger-only flows
- Approve / publish / schedule **from AI Chat** (human UI on Review Queue / Asset pages only)
- Publish now (immediate queue without `scheduled_at`)
- Rich text editor

## Related docs

- [ui_demo_readiness_audit.md](./ui_demo_readiness_audit.md) — MVP scope, limits, safety boundaries (UI.12 freeze)
- [ui_invariants.md](./ui_invariants.md) — UI rules checklist
- [web/README.md](../web/README.md) — setup and click-path summary
- [DEVELOPMENT.md](./DEVELOPMENT.md) — backend conventions

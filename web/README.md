# Marketsynth Web — Internal Operations UI

> Official product name: **Marketsynth**.  
> Former working name: **BotFazer** (legacy package / env identifiers remain until a controlled migration).

Phase **UI.12**: demo freeze audit — MVP ready for internal testers. See [docs/ui_demo_readiness_audit.md](../docs/ui_demo_readiness_audit.md) and [docs/ui_invariants.md](../docs/ui_invariants.md).

## Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS v4
- shadcn/ui (minimal — `Button` installed)
- TanStack Query

## Quick start (demo-ready)

### 1. Run the API

From the repository root:

```powershell
uv sync --extra dev
copy .env.example .env
uv run uvicorn app.main:app --reload
```

API default: http://127.0.0.1:8000

### 2. Seed demo data

Still from the repo root (creates user, project, campaign, channel, plan, assets, review item, scheduled job):

```powershell
uv run python scripts/seed_demo_marketing_flow.py
```

For a **fresh local sqlite** file (recommended on first setup):

```powershell
$env:DATABASE_URL="sqlite+aiosqlite:///./botfazer.db"
uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key
```

On first run this prints values for `web/.env.local`. If a demo API key already exists:

```powershell
uv run python scripts/seed_demo_marketing_flow.py --refresh-api-key
```

PostgreSQL deployments should run `uv run alembic upgrade head` before seeding (the script uses `create_all` for sqlite dev only).

### 3. Configure the web app

```powershell
cd web
copy .env.example .env.local
```

Paste from the seed output:

```env
NEXT_PUBLIC_BOTFAZER_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_BOTFAZER_API_KEY=bfz_...
NEXT_PUBLIC_BOTFAZER_PROJECT_ID=<uuid>
```

### 4. Run the UI

```powershell
npm install
npm run dev
```

Open http://localhost:3000

## Demo click-path

After seeding, walk through the full ops loop:

1. **Dashboard** (`/`) — metrics: campaigns, pending review, scheduled publications
2. **Campaigns** (`/campaigns`) — open **Q2 Launch Demo**
3. **Campaign detail** — workflow state badge, plan drafts, publication calendar, asset links
4. **Plan draft** — open **Demo launch plan** → **Generate draft assets** (idempotent if already generated)
5. **Review** (`/review`) — approve a draft asset (one should remain pending)
6. **Asset** (`/assets/{id}`) — edit draft revision or open approved asset → **Schedule publication**
7. **Calendar** — back on campaign detail, see scheduled job in publication calendar

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Dashboard (operational metrics) |
| `/campaigns` | list, create, status filter, include archived |
| `/campaigns/[id]` | overview, workflow, plan drafts, edit, archive |
| `/review` | Review queue |
| `/assets/[id]` | Asset editor |
| `/settings/channels` | Telegram publishing channels |

## Environment

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_BOTFAZER_API_BASE_URL` | API base URL (default `http://127.0.0.1:8000`) |
| `NEXT_PUBLIC_BOTFAZER_API_KEY` | Bearer token (required for data) |
| `NEXT_PUBLIC_BOTFAZER_PROJECT_ID` | Project UUID for scoped routes |

Missing `API_KEY` or `PROJECT_ID` shows a config hint instead of failing silently.

## UI polish (UI.10)

- **Empty states** with CTAs: create campaign, create Telegram channel, create plan draft, review queue hint
- **Status badges** — shared `StatusBadge` / `WorkflowStateBadge` / `ContentAssetStatusBadge`
- **Loading** — skeleton placeholders via `QueryStatus` (`loadingVariant`)
- **Errors** — consistent `ErrorPanel` on failed queries
- **Dates** — `formatDateTime()` everywhere in the UI

## Feature notes (UI.3–UI.9)

### Human review

- `POST .../content-assets/{id}/approve` and `/archive` — UI only
- Archive requires confirmation; toasts on success/error

### Schedule publication

- `GET .../publishing-channels` + `POST .../publication-jobs` with future `scheduled_at` (UTC)
- Approved assets only; local datetime → UTC in the browser

### Campaigns & plan drafts

- Campaign CRUD on `/campaigns` and `/campaigns/[id]`
- Plan drafts: create, generate assets, archive (no approve/publish from plan UI)

### Content asset revisions

- Draft: `POST .../content-assets/{id}/revisions`
- Approved: `POST .../create-revision` → new draft asset
- Version history with per-version preview

### Publishing channels

- Telegram: `name`, `chat_id`, `parse_mode`, `disable_web_page_preview`
- Bot token on API server only (`TELEGRAM_PUBLICATION_BOT_TOKEN`)

## Manual QA & tester round

| Doc | Purpose |
|-----|---------|
| [ui_demo_script.md](../docs/ui_demo_script.md) | **Presenter script** (~15 min live demo) |
| [ui_tester_feedback_template.md](../docs/ui_tester_feedback_template.md) | **Feedback form** per session |
| [ui_troubleshooting.md](../docs/ui_troubleshooting.md) | Common setup/runtime fixes |
| [ui_demo_smoke_checklist.md](../docs/ui_demo_smoke_checklist.md) | Step-by-step smoke (14 steps) |
| [ui_demo_readiness_audit.md](../docs/ui_demo_readiness_audit.md) | What MVP covers / limits / safety |
| [ui_invariants.md](../docs/ui_invariants.md) | UI rules that must not break |

**UI.13 (product analytics)** is deferred until after tester feedback — [ui_13_product_analytics_deferred.md](../docs/ui_13_product_analytics_deferred.md).

## Demo freeze verification

Run before inviting an internal tester:

```powershell
# from repo root
uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key

cd web
npm run lint
npm run build
```

Then paste seed output into `web/.env.local`, start API + `npm run dev`, and walk [ui_demo_smoke_checklist.md](../docs/ui_demo_smoke_checklist.md).

## Next phase

Drag-and-drop calendar, version diff UI, optional login.

# BotFazer — Demo script (internal MVP)

**Audience:** PM, marketer, or engineer evaluating the ops UI.  
**Duration:** 12–18 minutes (core path ~15 min).  
**Prerequisite:** [web/README.md](../web/README.md) setup + demo seed completed.

**Not a sales pitch for public SaaS** — position as: *“human-in-the-loop marketing ops console wired to our API.”*

---

## Before you start (2 min, off-screen)

1. API: `uv run uvicorn app.main:app --reload` → http://127.0.0.1:8000/health OK  
2. Seed: `uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key`  
3. Web: paste `NEXT_PUBLIC_*` into `web/.env.local`, `npm run dev` → http://localhost:3000  
4. Close Swagger — demo is **UI-only**

**Opening line (RU):**  
«Это внутренняя консоль операций: кампания → план → черновики контента → ревью человеком → публикация по расписанию. Агенты не апрувят и не публикуют сами.»

**Opening line (EN):**  
“This is our internal ops console: campaign → plan → draft assets → human review → scheduled publication. Agents don’t approve or publish on their own.”

---

## Act 1 — Situation on the dashboard (2 min)

**Go to:** `/`

**Say:**

- Metrics are scoped to **one project** from env (demo project after seed).
- **Pending review** = draft assets waiting for a human decision.
- **Scheduled publications** = jobs with a future time (not “sent to Telegram” unless worker + bot token configured).

**Show:** Health line in header (API / DB / Redis).

**Optional:** Mention seed already created data — you’re not starting from zero.

---

## Act 2 — Campaign context (3 min)

**Go to:** `/campaigns` → open **Q2 Launch Demo**

**Say:**

- A **campaign** groups plan, assets, and publication calendar.
- **Workflow state** is a read model (where the campaign is in the ops funnel).
- **Plan drafts** are planning artifacts; generating assets does **not** auto-approve or auto-publish.

**Show:**

- Overview counts (assets draft/approved, jobs scheduled).
- **Publication calendar** — seed should show one **scheduled** job.
- **Campaign assets** — links to asset editor.

**Skip unless asked:** Edit campaign, archive campaign (mention confirm dialog).

---

## Act 3 — Plan → assets (3 min)

**Stay on:** campaign detail → **Plan drafts**

**Say:**

- Strategist/planner output lands as a **plan draft** (structured `content_items`).
- **Generate draft assets** creates one draft asset per item (idempotent on repeat).

**Do (pick one):**

- Open **Demo launch plan** → click **Generate draft assets** → toast with count or “already generated”.
- Or only narrate if seed already generated: “three Telegram posts are now draft assets.”

**Point to:** Hint linking to **Review Queue** after generate.

**Do not claim:** Agents approved anything from this screen.

---

## Act 4 — Human review gate (3 min)

**Go to:** `/review`

**Say:**

- Only **humans** approve here (HTTP/UI), not agent tools.
- Queue shows **metadata only** (title, version) — open asset for full body.
- **Archive** requires confirmation; no publish side-effect.

**Do:**

- **Approve** one pending draft (seed leaves at least one).
- Show row disappearing and toast.

**Optional:** Click asset title → `/assets/{id}` to show editor.

---

## Act 5 — Asset editor & schedule (4 min)

**Go to:** `/assets/{id}` for an **approved** asset (or approve one first)

**Say:**

- **Draft:** edit title/body → **Create revision** (new version, stays draft).
- **Approved:** can **schedule publication** or start a **new draft revision** from approved (source unchanged).
- No rich text — intentional for MVP.
- **No publish now** — must pick a **future** time; UI sends UTC to API.

**Do:**

- Expand **Schedule publication** → pick **Demo Telegram** channel → future datetime → submit.
- Return to campaign → **Publication calendar** → show new or updated **scheduled** job.

**Show (optional):** **Reschedule** and **Cancel** on scheduled job (confirm on cancel).

---

## Act 6 — Channels & safety (2 min)

**Go to:** `/settings/channels`

**Say:**

- Channel stores **chat_id** and display options only.
- **Bot token lives on API server** (`TELEGRAM_PUBLICATION_BOT_TOKEN`), not in this form.
- Real Telegram send = worker + env; UI only schedules.

**Close with boundaries:**

| Human (UI) | Not in MVP |
|------------|------------|
| Approve, archive, schedule, reschedule, cancel | Login, billing, multi-tenant |
| Plan + generate drafts | Agent approve/publish |
| | Publish now button |

---

## After the demo (tester)

Ask them to fill [ui_tester_feedback_template.md](./ui_tester_feedback_template.md) within 24–48h while memory is fresh.

**Q&A prep:**

- “Can the AI approve?” → No, by design.  
- “Why no login?” → Internal demo; API key in env.  
- “Did it post to Telegram?” → Only if worker + token; scheduling is what UI proves.  
- “Can we use Postgres?” → Yes; migrations + seed; see troubleshooting.

---

## Variants

| Time | Cut |
|------|-----|
| **10 min** | Acts 1, 2, 4, 5 (skip plan create, skip channels deep-dive) |
| **20 min** | Full script + live create plan draft + second approve + reschedule |
| **Repeat demo** | Re-run seed or use filters; narrate idempotent generate |

---

## Related

- [ui_demo_smoke_checklist.md](./ui_demo_smoke_checklist.md) — QA steps with API names  
- [ui_demo_readiness_audit.md](./ui_demo_readiness_audit.md) — scope & limits  
- [ui_troubleshooting.md](./ui_troubleshooting.md) — when something breaks  

**Deferred:** [UI.13 product analytics](#) — event table (`campaign_created`, etc.) after tester feedback round.

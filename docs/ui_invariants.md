# UI invariants (Internal Operations UI)

Checklist of **must-remain-true** behaviors for `web/`. Used for demo freeze (UI.12), regression review, and tester expectations.

When adding UI features, verify these invariants still hold unless the product explicitly changes policy.

---

## Human-only gates

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| H1 | **No publish now** | Schedule form requires `datetime-local` + `scheduled_at` sent to API; copy states “no immediate publish”. No button to create a job without `scheduled_at`. |
| H2 | **No approve via agent tools** | Approve exists only as UI → `POST .../content-assets/{id}/approve`. Agent tool matrices exclude approve/publish write gates (backend). |
| H3 | **No schedule/publish via agent tools** | Publication jobs created from UI or direct HTTP API calls by humans/services — not from agent executor buttons in UI. |

---

## Secrets and configuration

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| S1 | **API key only via env** | `NEXT_PUBLIC_BOTFAZER_API_KEY` read from `web/.env.local` / build env; `getApiKey()` in `src/lib/api/config.ts`. No in-app key entry or storage. |
| S2 | **Bot token not in UI** | Telegram channel form: `name`, `chat_id`, `parse_mode`, `disable_web_page_preview` only. UI copy points to `TELEGRAM_PUBLICATION_BOT_TOKEN` on API server. |
| S3 | **Channel form rejects secrets** | Form does not expose token/password fields; `buildTelegramChannelConfig` only maps allowed keys. Any extra secret must not be added to channel create UI without security review. |
| S4 | **Do not commit env files** | `.env.local` gitignored; seed prints key once — document only in private notes. |

---

## Confirmations and destructive actions

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| C1 | **Archive asset requires confirm** | `ConfirmDialog` in asset editor and review actions before `POST .../archive`. |
| C2 | **Archive campaign requires confirm** | `CampaignDetailHeaderActions` confirm before campaign archive. |
| C3 | **Archive plan draft requires confirm** | `PlanDraftDetailPanel` confirm before plan archive. |
| C4 | **Archive channel requires confirm** | `PublishingChannelsTable` confirm before channel delete/archive. |
| C5 | **Cancel scheduled job requires confirm** | `ScheduledPublicationJobRow` confirm before cancel. |

---

## Scheduling and time

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| T1 | **Schedule only in the future** | `localDatetimeInputToUtcIso` in `src/lib/datetime.ts` rejects past times client-side; API validates future UTC `scheduled_at`. |
| T2 | **Local input → UTC for API** | Schedule and reschedule forms convert browser local `datetime-local` to ISO UTC before `POST` publication-jobs. |
| T3 | **Reschedule shows UTC preview** | Forms display “Sent to API as UTC” preview where applicable. |
| T4 | **Display uses consistent formatting** | `formatDateTime()` for tables and detail views. |

---

## Review queue and content safety

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| R1 | **Review queue without body leaks** | API `ReviewQueueItem` has title, status, version, campaign metadata — **no `body`**. UI table does not fetch or render full asset body on `/review`. |
| R2 | **Open asset for full content** | Review row links to `/assets/{id}` for body and actions. |
| R3 | **Approve does not auto-schedule** | Approve mutation only calls approve endpoint; invalidation does not create publication jobs. |

---

## Scope and read models

| ID | Invariant | How it is upheld |
|----|-----------|------------------|
| P1 | **Project-scoped routes** | Campaigns, review, assets, channels use `NEXT_PUBLIC_BOTFAZER_PROJECT_ID`; missing id shows `ProjectIdMissing`. |
| P2 | **Dashboard uses project metrics** | When `PROJECT_ID` set, `GET /projects/{id}/operational-metrics` (not owner-wide). |
| P3 | **Plan draft does not approve** | Generate assets only; copy states no approve/publish/schedule from plan section. |
| P4 | **Archived entities read-only** | Archived campaign/plan/asset UI disables edit/generate where implemented. |

---

## Explicit non-goals (do not add without new phase)

- Login / registration / password UI  
- Billing, invoices, usage meters  
- “Publish now” or “Send to Telegram” test button in ops UI  
- Agent-facing approve / publish buttons in UI  
- API key CRUD in web settings  
- Bot token input in channel form  

---

## Quick regression checklist

Before calling a build demo-ready:

- [ ] Grep web for `publish now` / immediate publish — should not exist  
- [ ] Schedule form still requires future datetime  
- [ ] Review page has no asset `body` column  
- [ ] Channel create form has no token field  
- [ ] Archive flows still use `ConfirmDialog`  
- [ ] `npm run lint` && `npm run build` pass  

See also: [ui_demo_readiness_audit.md](./ui_demo_readiness_audit.md), [ui_demo_smoke_checklist.md](./ui_demo_smoke_checklist.md).

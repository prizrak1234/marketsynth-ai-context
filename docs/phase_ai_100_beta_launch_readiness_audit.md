# Phase AI.100 — Beta launch readiness audit

**Status:** Production freeze (AI.96–AI.100).  
**Prerequisite:** [AI.95 Beta QA loop](phase_ai_95_beta_qa_readiness_audit.md).

## Goal

Prepare **controlled closed beta** for real testers: access gate, tester guide, demo reset, smoke command, launch checklist — **no new product features**.

**Out of scope:** billing, new agents/providers, Instagram/LinkedIn, background scheduler worker, new generation/publishing features.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.96** | `beta_access_status` on users + `GET /me/beta-access` + admin approve/block |
| **AI.97** | `GET /me/beta-guide` + dashboard Beta guide card |
| **AI.98** | `POST /projects/{id}/demo-flow/reset` (dev/admin, idempotent) |
| **AI.99** | `scripts/smoke_beta_launch.py` |
| **AI.100** | **Freeze** — this doc + `test_phase_ai_100_beta_launch_freeze.py` |

---

## Beta access gate (AI.96)

| Status | MVP API access |
|--------|----------------|
| `pending` | Blocked (403 `beta_access_pending`) except beta-access, beta-guide, beta-feedback, beta-admin |
| `approved` | Full MVP paths |
| `blocked` | 403 `beta_access_blocked` |

Development (`APP_ENV=development`) bypasses the gate. New users in development are auto-approved on create.

```bash
GET  /me/beta-access
POST /me/beta-admin/users/{user_id}/approve-beta   # body: {"notes":"optional"}
POST /me/beta-admin/users/{user_id}/block-beta
```

Env: `BETA_ACCESS_GATE_ENABLED=true` (default). Disable only for local experiments.

---

## Tester guide (AI.97)

```bash
GET /me/beta-guide
```

Read-only: current phase, what to test, expected path (onboarding → chat → plan → asset → media → package → dry-run publish), known limitations, feedback instructions.

UI: Dashboard **Beta guide** card.

---

## Demo reset (AI.98)

```bash
POST /projects/{project_id}/demo-flow/reset
```

- Dev or `DEMO_FLOW_ENDPOINTS_ENABLED=true`
- Production: `admin` or `owner` role
- Removes E2E demo plan chain only (not project, agents, API keys)
- Idempotent: second call returns `cleared: false`

---

## Smoke command (AI.99)

```bash
uv run python scripts/smoke_beta_launch.py
```

Checks (in-process, no external APIs):

1. Alembic at head (`20260603_0021`+) — skip with `--skip-alembic`
2. E2E demo seed
3. Demo flow status (`publication_job_status=queued`)
4. QA export safe (no secrets/bodies)
5. Dry-run dispatch on demo job
6. Beta guide content present

Exit code **1** on failure.

---

## Launch checklist

### Environment

- [ ] `APP_ENV=production` or `staging`
- [ ] `BETA_ACCESS_GATE_ENABLED=true`
- [ ] `BETA_ADMIN_ENDPOINTS_ENABLED=true` (or restrict admin to known owners)
- [ ] `DEMO_FLOW_ENDPOINTS_ENABLED` as needed for testers (status only; reset stays admin)
- [ ] `BETA_LIMITS_ENABLED=true`
- [ ] Secrets in `.env` only — never in repo
- [ ] `TELEGRAM_PUBLISHING_ENABLED=false` unless real send is intentional

### Tester onboarding

- [ ] Create user + API key
- [ ] `POST .../approve-beta` for each tester
- [ ] Share `GET /me/beta-guide` summary and dashboard link
- [ ] Optional: `uv run python scripts/seed_e2e_demo.py` for shared demo project id

### Pre-launch verification

```bash
uv run alembic upgrade head
uv run pytest tests/test_phase_ai_100_beta_launch_freeze.py tests/test_phase_ai_95_beta_qa_readiness_freeze.py -q
uv run python scripts/smoke_beta_launch.py
```

**First wave (5–10 testers):** [beta_runbook_first_wave.md](beta_runbook_first_wave.md) — один сценарий, три метрики, без массового invite.

---

## Rollback notes

| Issue | Action |
|-------|--------|
| Gate blocks everyone | Set `BETA_ACCESS_GATE_ENABLED=false` temporarily or approve users via admin API |
| Bad demo seed | `POST .../demo-flow/reset` then re-run `scripts/seed_e2e_demo.py` |
| Smoke fails on dispatch | Check publication job still `queued`; reset + re-seed |
| Feedback noise | Use beta-admin triage/resolve; not a support CRM |

---

## Known out-of-scope

- Billing and subscriptions
- Instagram / LinkedIn
- Background scheduler worker loop
- New agents or LLM providers
- Support ticketing / SLA

---

## Regression commands

```bash
uv run pytest tests/test_phase_ai_100_beta_launch_freeze.py tests/test_phase_ai_95_beta_qa_readiness_freeze.py tests/test_phase_ai_90_beta_readiness_freeze.py -q
```

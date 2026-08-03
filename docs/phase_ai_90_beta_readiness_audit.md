# Phase AI.90 — Beta readiness audit

**Status:** Production freeze (AI.86–AI.90).  
**Prerequisite:** [AI.85 MVP demo](phase_ai_85_mvp_demo_readiness_audit.md).

## Goal

Prepare controlled tester access: onboarding, soft limits, safe API errors, admin visibility — **no new product features**.

**Out of scope:** billing, public launch, new agents/providers, Instagram/LinkedIn, background scheduler worker.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.86** | Onboarding steps + `GET/POST /me/onboarding*` + dashboard checklist |
| **AI.87** | `BetaLimitsService` — 429 envelopes, generous dev / strict staging+prod |
| **AI.88** | `ApiErrorResponse` + global handlers + `X-Request-ID` |
| **AI.89** | `GET /me/beta-admin/dashboard` (dev or `BETA_ADMIN_ENDPOINTS_ENABLED`) |
| **AI.90** | **Freeze** — this doc + `test_phase_ai_90_beta_readiness_freeze.py` |

---

## Onboarding (AI.86)

| Step | Detection |
|------|-----------|
| `project_created` | User has ≥1 project |
| `agents_seeded` | Orchestrator + copywriter agents on scoped project |
| `demo_seeded` | E2E demo project name **or** manual `POST /me/onboarding/complete-step` |
| `first_chat_done` | ≥1 agent chat message on project |
| `first_asset_created` | ≥1 content asset on project |
| `first_publication_job_created` | ≥1 publication package job on project |

```bash
GET /me/onboarding?project_id={uuid}
POST /me/onboarding/complete-step  # body: {"step":"demo_seeded"} only
```

---

## Soft limits (AI.87)

| Limit | Scope | Default (dev) | Strict (staging/prod) |
|-------|--------|---------------|------------------------|
| Projects | per user | 100 | 10 |
| Chat sessions | per project | 500 | 50 |
| Marketing plans | per project | 200 | 25 |
| Generation jobs | per user/project/day | 500 | 30 |
| Publication jobs | per user/project/day | 500 | 40 |

Disable all: `BETA_LIMITS_ENABLED=false`

Exceeded → **429** with `error_code` + `safe_message` (+ `limit` in details).

---

## Error envelope (AI.88)

All mapped errors return:

```json
{
  "error_code": "rate_limit_exceeded",
  "safe_message": "Human-safe message",
  "details": {},
  "request_id": "uuid"
}
```

Handlers cover: `RateLimitExceededError`, `InvalidStateError`, `NotFoundError`, `HTTPException`, validation, generic 500 (no stack trace).

Response header: `X-Request-ID`.

---

## Beta admin (AI.89)

```bash
GET /me/beta-admin/dashboard
```

Returns counts only: users, projects, demo-ready E2E projects, failed jobs (24h window), `latest_activity_at`. No payloads, tokens, or content bodies.

Access: development **or** `BETA_ADMIN_ENDPOINTS_ENABLED=true` (+ admin/owner in production).

---

## Regression

```bash
uv run alembic upgrade head
uv run python scripts/seed_e2e_demo.py
uv run pytest \
  tests/test_phase_ai_90_beta_readiness_freeze.py \
  tests/test_phase_ai_80_e2e_demo_seed.py \
  tests/test_phase_ai_81_demo_flow_status.py \
  tests/test_phase_ai_84_mvp_safety_regression.py \
  tests/test_phase_ai_85_mvp_demo_freeze_invariants.py -q
```

---

## UI

- Dashboard: **First-run onboarding** checklist (`FirstRunChecklist`)
- Existing **MVP demo flow** checklist unchanged (AI.82)

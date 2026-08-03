# Phase AI.95 — Beta QA readiness audit

**Status:** Production freeze (AI.91–AI.95).  
**Prerequisite:** [AI.90 Beta readiness](phase_ai_90_beta_readiness_audit.md).

## Goal

Closed-beta **diagnostics only**: testers report where the MVP path breaks; admins triage and export safe aggregates — **not** a support desk, billing, or new product surface.

**Out of scope:** billing, new providers/agents, real Instagram/LinkedIn, background scheduler worker, raw error dumps, prompts, content bodies.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.91** | `BetaFeedbackReport` + `POST/GET /me/beta-feedback*` + sanitized `safe_context` |
| **AI.92** | `GET/POST /me/beta-admin/feedback*` triage/resolve + admin table UI |
| **AI.93** | Demo flow `failed_step`, `blocking_reason`, `last_error_code`, `suggested_next_action` |
| **AI.94** | `GET /me/beta-admin/qa-export` — safe JSON aggregates |
| **AI.95** | **Freeze** — this doc + `test_phase_ai_95_beta_qa_readiness_freeze.py` |

---

## Feedback reports (AI.91)

Entity: `BetaFeedbackReport` in `app/schemas/contracts.py`.

| Field | Notes |
|-------|--------|
| `source` | `onboarding` \| `chat` \| `marketing_pipeline` \| `content` \| `media` \| `publishing` \| `other` |
| `severity` | `low` \| `medium` \| `high` \| `blocker` |
| `status` | `open` \| `triaged` \| `resolved` \| `archived` |
| `safe_context` | Allow-listed keys only; forbidden tokens stripped |

```bash
POST /me/beta-feedback
GET  /me/beta-feedback?status=open
GET  /me/beta-feedback/{id}
POST /me/beta-feedback/{id}/archive
```

Rules: `sanitize_text` on title/description; `sanitize_feedback_context` — no secrets, no raw payload dumps.

---

## Admin triage (AI.92)

Dev or `BETA_ADMIN_ENDPOINTS_ENABLED=true`; production requires `admin` or `owner` role.

```bash
GET  /me/beta-admin/feedback?source=publishing&severity=blocker&status=open
POST /me/beta-admin/feedback/{id}/triage
POST /me/beta-admin/feedback/{id}/resolve
```

UI: **Settings → Beta QA** — feedback table + triage/resolve actions.

---

## Demo failure markers (AI.93)

`GET /projects/{id}/demo-flow/status` adds:

- `failed_step` — coarse area (`marketing_pipeline`, `content`, `media`, `publishing`, …)
- `blocking_reason` — human-safe sentence (no stack traces)
- `last_error_code` — from structured `error_code` only (max 64 chars)
- `suggested_next_action` — mirrors `next_available_action`

Dashboard checklist shows an amber banner when `failed_step` is set.

---

## QA export (AI.94)

```bash
GET /me/beta-admin/qa-export
```

Returns:

- Demo project snapshots (id, name, job status, `failed_step`, `last_error_code`)
- Demo completion counts (total, queued, with failure marker)
- Feedback counts by status + blocker/high severity
- Failed job counts (24h window)

**Never includes:** descriptions, content bodies, prompts, provider payloads, API keys.

---

## Verification

```bash
cd botfazer
uv sync --extra dev
uv run alembic upgrade head
uv run pytest tests/test_phase_ai_95_beta_qa_readiness_freeze.py tests/test_phase_ai_90_beta_readiness_freeze.py -q
```

---

## Risk posture

| Risk | Mitigation |
|------|------------|
| Feedback becomes support CRM | Scope frozen to diagnostic fields; no assignments/SLA |
| Secrets in context | `safe_feedback_context` + publishing metadata scrubber |
| Raw errors to testers | Failure markers expose codes/reasons only |
| QA export leaks PII/content | Export schema excludes bodies and prompts |

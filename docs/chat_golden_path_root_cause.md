# Chat Golden Path — Root Cause Report

Status: **implementation_in_progress** (general_answer LLM + router matrix + Playwright A–H implemented; live E2E run requires dev credentials + servers)

## Proven root causes

### RC-1: Optimistic append + full hydrate (frontend)

**Location:** `web/src/components/workspace/home/home-execution-panel.tsx`

**Fix:** Removed optimistic append. Single path: POST → hydrate replace snapshot only.

### RC-2: No backend idempotency (backend)

**Location:** `app/services/user_requests_service.py`

**Fix:** `client_message_id` + `idempotency_key` with lookup-before-create.

### RC-3: Universal canned BIV stub (backend router)

**Fix:** `app/domain/user_request_assistant.py` — contextual responses for project/BIV routes.

### RC-4: No submit mutex (frontend)

**Fix:** `sendInFlightRef` guard + `submitState` state machine.

### RC-5: False-positive ambiguous-ads gate

**Fix:** Skip ambiguous-ads for long descriptive briefs (SaaS, агентство, кампания).

### RC-6: Template-only general chat (backend)

**Location:** No LLM path for ordinary questions — all unmatched text fell through to clarification templates.

**Fix:** `app/services/user_request_general_answer_service.py` — one LLM call per `general_answer` route; provider/empty failures → `FAILED` status; idempotent replay skips second LLM call.

### RC-7: Network retry new idempotency keys (frontend)

**Fix:** `pendingSubmitKeysRef` reuses `client_message_id` / `idempotency_key` when retrying the same draft text after failure.

## Metrics (before → after)

| Metric | Before (broken) | After (target) |
|--------|-----------------|----------------|
| POST per single click | 1–N | 1 |
| User DB rows per submit | 1–N | 1 |
| Assistant runs per submit | 1–N | 1 |
| Router decisions per submit | 1–N | 1 |
| LLM calls (general_answer) | 0 (template) | 1 |
| Rendered bubbles after hydrate | 2–2N | 2 (1 user + 1 assistant) |
| Refresh creates POST | sometimes | never |
| SaaS acceptance → canned BIV | yes | no — contextual project_action |

## Verification

### Unit / API (PASS)

```bash
uv run pytest tests/test_chat_general_answer.py tests/test_chat_router_matrix.py tests/test_chat_golden_path.py -q
# 32 passed
```

### Playwright A–H (requires live stack)

```bash
# Provision (development/test only)
export CHAT_GOLDEN_PATH_E2E_EMAIL=chat-golden-path-dev@example.com
export CHAT_GOLDEN_PATH_E2E_PASSWORD='...min 10 chars...'
uv run python scripts/chat_golden_path_provision_dev_user.py --update

export CPH3_E2E_EMAIL=$CHAT_GOLDEN_PATH_E2E_EMAIL
export CPH3_E2E_PASSWORD=$CHAT_GOLDEN_PATH_E2E_PASSWORD

# Terminal 1: uv run uvicorn app.main:app --reload
# Terminal 2: cd web && npm run dev
cd web && npx playwright test e2e/chat-golden-path.spec.ts --project=chromium
```

Artifacts: `web/test-results/chat-golden-path/{runId}/*.png`, Playwright traces on failure.

## Final gate

Status → `waiting_for_owner_validation` only when:

- [ ] Playwright A–H PASS (live)
- [ ] Exact acceptance case PASS (live + screenshots)
- [ ] DB assertions PASS in E2E
- [ ] No blocker/critical/high known issues

Until live E2E PASS: **implementation_in_progress**. QA-01 not opened.

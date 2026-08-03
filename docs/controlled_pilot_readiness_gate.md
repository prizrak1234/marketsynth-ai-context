# Controlled Pilot Readiness Gate

**Date:** 2026-07-15  
**Code checkpoint:** `34f0c90` `ops: complete controlled pilot hardening`  
**Docs checkpoint:** `9444c8b` `docs: record controlled pilot readiness gate CONDITIONAL_GO`  
**Branch:** `master` (local only)  
**Active DB:** `botfazer_cph1` @ Alembic `20260715_0037`  
**Canonical frontend host:** `http://localhost:3000`  
**Canonical backend API:** `http://localhost:8000`

## Final verdict

**CONDITIONAL_GO**

Limited 1–3 user pilot is acceptable only after the explicit conditions in
[controlled_pilot_conditions.md](controlled_pilot_conditions.md) are closed —
chiefly a real **HTTPS cutover** with Secure cookies and matching origins for any
non-local user access.

Local production-like evidence is strong; remote access is not yet approved.

## Area scores

| Area | Score |
|------|-------|
| A. Product integrity | PASS |
| B. Data integrity | PASS |
| C. Authentication | PASS |
| D. Owner isolation | PASS |
| E. Migration safety | PASS |
| F. Backup/restore | PASS |
| G. Health/readiness | PASS |
| H. Logging and diagnostics | PASS |
| I. Security configuration | PASS_WITH_CONDITIONS (HTTPS/Secure for remote) |
| J. Browser UX | PASS |
| K. Error handling | PASS |
| L. Rollback | PASS (dry-run documented) |
| M. Deployment repeatability | PASS_WITH_CONDITIONS (local OPTION B proven; remote edge pending) |
| N. Execution firewall | PASS |
| O. Pilot operations | PASS_WITH_CONDITIONS (operator/on-call contacts + schedule) |

## Mandatory login check (executed)

Characterization via Playwright gate suite `e2e/readiness-gate-login.spec.ts`
against live local stack:

| Host | Initial error absent | Invalid after submit | Valid login + cookie | Refresh session | Logout enforces /login |
|------|----------------------|----------------------|----------------------|-----------------|------------------------|
| `http://localhost:3000` (canonical) | PASS | PASS | PASS | PASS | PASS |
| `http://127.0.0.1:3000` (alias) | PASS | PASS | PASS | PASS | PASS |

Canonical choice: **localhost**. CORS/CSRF allowlists include both loopbacks;
API host is rewritten to the page hostname so cookies stay same-site.
Playwright defaults and `.env.local` use localhost.

Previous defect (invalid credentials shown before submit) is **closed** in product
code and verified on both hosts — not only with API TestClient.

## Evidence summary

- Pytest CPH.1–CPH.5 targeted: 44 passed
- Playwright auth + commercial happy path: 9 passed
- Gate login matrix: 2 passed
- `/health/live` + `/health/ready` OK on `botfazer_cph1`
- Post-deploy smoke OK; correlation IDs captured
- CPH.4 backup manifest `cph4_botfazer_cph1_20260715T183230Z` restore_test_status=`passed`
- Rollback dry-run OK (non-destructive)
- Production `next build` previously passed in CPH.5

## Why not GO

GO requires a valid **HTTPS remote deployment plan** that is actually operable for
external users (Secure cookies, canonical public origins). Local HTTP pilot proof
is insufficient to approve network-exposed users.

## Why not NO_GO

No open P0 in auth, isolation, integrity, migration guard, backup restore, or
execution firewall for the local controlled path.

## Why not INSUFFICIENT_DATA

Manual-equivalent login matrices, E2E commercial path, backup restore evidence,
and readiness endpoints were executed against the live stack.

## Owner next action

1. Approve or edit conditions in `controlled_pilot_conditions.md`.
2. Complete HTTPS cutover (Caddy/TLS or equivalent) before inviting remote users.
3. Only then invite ≤3 named pilot users under the defined scope.

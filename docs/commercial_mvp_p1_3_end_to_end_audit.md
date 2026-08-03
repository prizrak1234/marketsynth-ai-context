# Commercial MVP P1.3 — End-to-End Audit

## Scope

Audit-first freeze of:

Project → ProjectBrief → Investigation → Source → Evidence → BusinessVerdict → MarketingStrategy → ImplementationPlan → Handoff → MarketingPlan Draft

No new business domain. A7 / AI.592 / V2.2 paused.

## Checkpoint

- P1.2: `82ea2ce` — `feat: add controlled MarketingPlan draft handoff`
- Alembic code head: `20260614_0036`
- Local Postgres drift `20260608_0033` unchanged (do not repair in P1.3)

## Verdict

Commercial chain is coherent: parent version pins on write, owner scoping via `require_project_owner`, approved objects immutable, handoff draft-only + idempotent + firewalled.

## Defects patched in P1.3

1. Alembic static chain test extended to `0035`/`0036`.
2. Full E2E freeze tests through MarketingPlan draft.
3. Cross-owner handoff/MarketingPlan isolation test.
4. Fingerprint reproducibility invariant.
5. FE honesty: I6 write-policy/messages updated for controlled P1.2 handoff (no longer claim “API missing”).

## Not patched (documented gaps)

- Local PostgreSQL alembic state drift
- Full historical alembic on SQLite (legacy ALTER unsupported)
- Browser E2E
- MarketingPlan review UI
- Server-side Next.js route middleware (APIs remain SoT)

## Classification

**B → near C:** Internal alpha with controlled-pilot path if hardening P0 gaps are closed. Not production-ready.

# CPH.1 — Migration repair options

## Observed facts

1. Code head: linear `… → 20260614_0036`.
2. Local `botfazer` stamped `20260608_0033` (missing from tree); commercial tables absent; AI.60x tables present.
3. Fresh PostgreSQL database upgrades **successfully** from base to head (disposable `botfazer_cph1`).
4. Exact orphan migration script **not** recoverable from local git → Option E blocked.
5. Silent `alembic stamp head` would hide drift without schema proof → **rejected**.

## Options

| Option | Description | Fit |
|--------|-------------|-----|
| **A** Append compatibility migration | Normalize an already-upgraded DB after head | Poor for orphan stamp: DB is not “past head”; it is on an unknown line |
| **B** Edit historical migration | Dialect-safe fix in old file | **Default deny.** Only if proven never shared; here PG full upgrade already works |
| **C** Official baseline / stamp procedure for **new** DBs | Create empty DB → migrate (or reviewed baseline) → stamp known revision | **Recommended for pilot** |
| **D** Squashed pilot baseline + keep old history | New single baseline for greenfield; leave old chain for relics | Optional later if bootstrap ever fails; **not required now** (PG chain works) |
| **E** Restore missing migration file | Need exact content + down_revision | **Unavailable** (no local artifact) |
| **F** Rebuild local DB from backup into clean schema | Export → new schema → selective import | Only with **owner approval**; not executed in CPH.1 |

## Recommended path

**Option C for pilot / Commercial MVP work:**

1. Keep `botfazer` frozen as legacy+WIP artifact (backed up).
2. Use `botfazer_cph1` (or `botfazer_pilot`) created empty, `alembic upgrade head`, revision `20260614_0036`.
3. Point app `DATABASE_URL` at disposable/pilot DB for CPH.2+.
4. Defer Option F rebuild of `botfazer` until owner approves and CPH.4 ops practices land.

**Do not** use Option B to “fix” `20260608_0033`.  
**Do not** stamp `botfazer` to `20260614_0036`.

## Legacy failure note

Initial concern: “full Alembic upgrade from base fails on legacy ALTER.”

**On PostgreSQL 17 (this machine):** full upgrade to head **succeeds**.  
`batch_alter_table` migrations exist (e.g. `20260529_0003`, `0010`, `0013`) and are compatible with PG here.  
Any prior failure was likely SQLite/target mix-up, wrong DB, or orphan-revision `current` errors — not a need to rewrite history for Commercial MVP bootstrap.

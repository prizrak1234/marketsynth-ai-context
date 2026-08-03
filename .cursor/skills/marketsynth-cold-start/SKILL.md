---
name: marketsynth-cold-start
description: >-
  Restores Marketsynth execution context from Source of Truth without guessing.
  Use at conversation start, after a long gap, when the owner asks where we are,
  what the active program/slice is, or what the single next step is. Read-only —
  does not change code.
---

# Marketsynth Cold Start

**Layer:** Cursor Development Governance (procedure).  
**Does not replace:** `AGENTS.md`, always-on rules, or owner Task IDs.  
**Invariant:** Invariants stay in rules; this skill only restores *where we are*.

## When to run

- New chat / cold session on Marketsynth
- Owner asks: active program, blockers, next step
- Before picking work if context is unclear

**Do not run** as a substitute for an approved Task ID when the owner already named the task.

## Forbidden

- Changing `app/`, `web/`, `tests/`, `alembic/`
- Starting implementation because “next step looks obvious”
- Inventing program status not present in SoT
- Opening parallel product programs
- Treating Capability Registry as authorization

## Procedure (mandatory order)

1. Read `AGENTS.md` (Cold Start Protocol + active track notes).
2. Read `knowledge/00_INDEX.md` (status snapshot + links).
3. Read `knowledge/06_CURRENT_STATE.md` — **`## Active Execution` first**.
4. Read `knowledge/05_ROADMAP.md` (approved roadmap only).
5. Read `knowledge/15_SESSION_LOG.md` (latest handoff entry).
6. If Active Execution points at a program pack (e.g. PRODUCT-02/03), open its index or freeze doc for status only.
7. Cross-check (lightweight, evidence-based):
   - SoT claim vs named docs on disk
   - Optional: `git status -sb` for dirty tree / branch (report only; do not “clean up”)
   - Do **not** run full test suites unless owner asks
8. Emit the **Cold Start Report** below.
9. **Stop.** Wait for owner instructions unless the owner already gave an explicit Task ID in the same message.

## Cold Start Report (required output)

```text
Program: …
Milestone / Task: …
Status: … (from SoT verbatim: OWNER-FROZEN | ready_for_owner_review | …)
owner_freeze: … | N/A
Last PASS / acceptance: … (or NOT SET)
Blockers: …
Forbidden now: …
Single next owner/agent step: … (one step only; cite SoT)
Contradictions: none | [list with paths]
Code changes this turn: none (cold start)
```

## Pass criteria for this skill

- Every field above filled from files (or explicit “missing doc”)
- No invented next task
- No code edits
---

## Anti-patterns

| Bad | Good |
|-----|------|
| “Next we should build Strategy Runtime” without SoT | Cite `06_CURRENT_STATE` Active Execution |
| Summarizing half the roadmap as “current” | One active priority only |
| Starting PRODUCT-01 work during PRODUCT-03 docs | Report contradiction; stop |

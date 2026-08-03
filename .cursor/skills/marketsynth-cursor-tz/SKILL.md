---
name: marketsynth-cursor-tz
description: >-
  Drafts Marketsynth Cursor task specs (ТЗ) in a fixed contract format. Use when
  the owner asks to write a Task ID / TZ / implementation brief, prepare the next
  slice prompt, or standardize a handoff for another agent or model. Does not
  implement the task unless the owner explicitly requests execution in the same
  message.
---

# Marketsynth Cursor TZ

**Layer:** Cursor Development Governance (procedure).  
**Output:** One copy-pasteable task brief.  
**Does not:** invent roadmap priority, start runtime, or set `owner_freeze`.

## When to run

- Owner asks for ТЗ / Task ID / slice brief / agent prompt
- After cold start, owner wants the *next* task written (not executed)
- Standardizing a docs-only or code task for another model

## Before drafting

1. Run or reuse **marketsynth-cold-start** facts (active program, blockers).
2. Confirm the task matches **one** active priority from `knowledge/06_CURRENT_STATE.md`.
3. If priority mismatch → draft only after owner confirms, or draft as **PROPOSED** clearly marked.

## Mandatory TZ contract (every draft)

Emit **all** sections below. Use Russian or English to match the owner request; keep section headers stable.

```markdown
# TASK ID:
[PROGRAM-SLICE-NN or explicit id]

# Название:
[one line]

# Тип:
[Docs-only | Product runtime | Frontend | Audit read-only | Governance | …]

# Приоритет:
[P0/P1/…] — [why this is the only active priority or PROPOSED]

# Текущий статус:
[from SoT]

────────────────────────────────────
1. КОНТЕКСТ
────────────────────────────────────
[Short. Link SoT + prior freeze/acceptance. No novel architecture.]

────────────────────────────────────
2. ОСНОВНАЯ ЦЕЛЬ
────────────────────────────────────
[Exactly one goal.]

────────────────────────────────────
3. ПРИЧИНА
────────────────────────────────────
[Why now; commercial or reliability link.]

────────────────────────────────────
4. SCOPE
────────────────────────────────────
[In scope bullets.]

────────────────────────────────────
5. OUT OF SCOPE
────────────────────────────────────
[Explicit bans — runtimes, IA, migrations, etc. as applicable.]

────────────────────────────────────
6. SOURCE OF TRUTH
────────────────────────────────────
[Mandatory reads: AGENTS, 00_INDEX, 06_CURRENT_STATE, 15_SESSION_LOG, + task docs.]

────────────────────────────────────
7. FILES / AUDIT TARGETS
────────────────────────────────────
[Concrete paths to inspect; “create only …” if docs pack.]

────────────────────────────────────
8. REQUIREMENTS
────────────────────────────────────
[Numbered, testable requirements.]

────────────────────────────────────
9. INVARIANTS
────────────────────────────────────
[PRODUCT-02 freeze / tenant / contracts-first / sanitize / no scope expansion / …]

────────────────────────────────────
10. COMPATIBILITY
────────────────────────────────────
[Must not break …; inherit …]

────────────────────────────────────
11. SECURITY / LOGGING / ERRORS
────────────────────────────────────
[Tenant boundaries; no secrets in logs; honest errors — or N/A for docs-only.]

────────────────────────────────────
12. TESTS
────────────────────────────────────
[Files/commands — or N/A with reason for docs-only.]

────────────────────────────────────
13. VERIFICATION COMMANDS
────────────────────────────────────
[Exact commands — or N/A.]

────────────────────────────────────
14. PASS CRITERIA
────────────────────────────────────
[Objective PASS list.]

────────────────────────────────────
15. FAIL CRITERIA
────────────────────────────────────
[Objective FAIL list.]

────────────────────────────────────
16. REPORT FORMAT
────────────────────────────────────
[Delivery report / owner report sections required.]

────────────────────────────────────
17. SoT UPDATES
────────────────────────────────────
[Which knowledge/* files to update after PASS — or none.]

────────────────────────────────────
18. STOP CONDITIONS
────────────────────────────────────
[When to halt for owner decision.]
```

## Quality bar

| Rule | Requirement |
|------|-------------|
| One goal | No multi-program TZ |
| No architecture freestyle | Map to frozen invariants; list owner decisions separately if needed |
| Docs vs code | Docs-only TZ must forbid `app/`/`web/`/`tests/` edits |
| Evidence | PASS must require tests/commands/API/browser/owner as applicable — skills alone ≠ PASS |
| Reviewers | If non-trivial product/runtime: require composite review / review-gate |
| Freeze | Never auto-set `owner_freeze` |

## After delivering TZ

**Stop** unless the owner says to execute the Task ID in the same message.

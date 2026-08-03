---
name: marketsynth-task-preflight
description: >-
  Mandatory pre-implementation check before Marketsynth product or runtime code
  changes. Use before editing app/, web/, tests/, alembic/, or scripts/ product
  paths; when starting an approved Task ID; or when tempted to code before root
  cause is proven. Aligns with marketsynth-planning-gate. Skip heavy form for
  pure docs/governance/read-only when the gate allows.
---

# Marketsynth Task Preflight

**Layer:** Cursor Development Governance (procedure).  
**Complements:** `.cursor/rules/marketsynth-planning-gate.mdc`  
**Does not replace:** owner-approved Task ID / TZ scope.

## When to run

**Required** before first edit to:

- `app/**`, `web/**`, `tests/**`, `alembic/**`, `scripts/**` (product/runtime)
- API contracts, DB models, frontend routes, user-facing product copy

**Skip heavy preflight** (one-line note, then proceed) for:

- Read-only audit / Q&A
- Docs-only under `docs/**` or `knowledge/**` with no code impact
- Cursor governance only (`.cursor/**`, `docs/cursor/**`)
- Single-line comment typo when owner says so

## Forbidden until preflight PASS

- “Implementing…” without proving problem and files
- Architecture redesign when Task ID + scope already approved
- Migrations / secrets / production / publish without owner decision
- Scope expansion beyond approved task
- Mixing infrastructure/governance tasks with product slices in one turn unless owner combined them

## Preflight checklist (output this block)

```text
1. Task ID: …
   Active product priority (06_CURRENT_STATE): …
2. Problem proven? yes/no — evidence (file/log/test/owner report): …
3. Simpler fix exists? yes/no/unknown — …
4. Matches current priority? yes/no — if no: STOP
5. Files to inspect/change: [concrete paths]
6. Current behavior (evidence: file/function): …
7. Target behavior (approved spec): …
8. Domain logic change? yes/no
9. In scope / out of scope: …
10. Invariants: tenant isolation · contracts-first · sanitize inbound · no scope expansion · [task-specific]
11. Migrations / schema? yes/no — if yes: owner decision required
12. Owner decision required? yes/no — reason
13. Tests to add or run: …
14. Verification commands: …
15. Contradictions with SoT/spec/code: none | …
16. Preflight verdict: PASS | STOP
```

## STOP rules

Stop implementation and ask owner if:

- Spec contradicts SoT or active slice
- Architecture / roadmap change not in approved task
- Irreversible migration without approval
- Scope ambiguous or expanded
- Secrets, production, or external publish without explicit approval
- Problem not proven (symptom-only)

## Do not STOP for re-approval when

- Task explicitly approved (Task ID in prompt)
- No contradictions
- Work stays within approved scope and invariants

## After PASS

Proceed to implementation **within scope only**.  
After non-trivial product/runtime changes, use skill **marketsynth-composite-review** (Stage 2 also: `marketsynth-review-gate` when present) before owner-facing PASS.

## Relation to commercial directive

If the change touches commercial UI, also satisfy Journey → IA → DESIGN → implementation gate from always-on commercial rules **before** coding screens.

# Commercial MVP P0.2 — Lifecycle and stages

## Statuses

`draft` → `ready` → `active` → `under_review` → `completed`

Side paths:

- `ready` / `active` → `blocked` → `ready` (resume)
- `draft` / `ready` / `active` → `cancelled` (terminal)
- `completed` → `superseded` (via explicit supersede + new row)

Rules:

- completed / cancelled / superseded are immutable except superseding completed;
- cancelled cannot resume;
- one **active** Investigation per Project;
- `active` requires submitted Brief + matching fingerprint at create time.

## Stages (frozen UX order)

1. `project_context`
2. `market_research`
3. `competitor_analysis`
4. `audience_analysis`
5. `demand_signals`
6. `economics`
7. `risk_assessment`
8. `evidence_review`
9. `verdict_preparation`

No progress percentages. Stages do not auto-start unless explicitly patched.

## Readiness (not Business Verdict)

`not_ready` | `conditionally_ready` | `ready_for_review`

Deterministic from lifecycle + stages; Source/Evidence coverage reasons marked **pending until P0.3/P0.4**.

## Active meaning in P0.2

Lifecycle state only — **no** Agent Run, LLM, provider, or external research.

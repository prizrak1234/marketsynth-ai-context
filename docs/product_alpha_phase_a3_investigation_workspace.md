# Product Alpha Phase A3 — Investigation Workspace & Evidence Layer

**Status:** COMPLETED (local)  
**Date:** 2026-07-13  
**Constraints:** Landing / Workspace / Intake preserved · mock evidence only · no final verdict · no backend

## Route

Primary (enhanced):

`/workspace/projects/[projectId]/investigation`

Demo project IDs (seeded locally):

| ID | Scenario |
|---|---|
| `proj_inv_a_conditional` | Conditionally ready |
| `proj_inv_b_not_ready` | Not ready |
| `proj_inv_c_ready` | Ready for review |

Example: http://localhost:3000/workspace/projects/proj_inv_a_conditional/investigation

## Page structure

1. Header — name, stage, intake readiness, investigation status, mock label  
2. Scenario reset (A/B/C)  
3. Investigation summary (from brief) + link to intake review  
4. Investigation pipeline (9 stages)  
5. Agency Runtime Monitor (reused; detail encodes area / artifacts / blocker)  
6. Sources  
7. Evidence Register (+ filters)  
8. Findings (facts vs hypotheses distinguished)  
9. Missing data (local resolve actions)  
10. Risks / Opportunities  
11. Contradictions  
12. Verdict readiness (not GO/NO_GO) + CTA «Подготовить вердикт» (disabled when not_ready; ack required when conditional)

## Models

`web/src/lib/investigation/`

- `types.ts` — workspace domain types  
- `mock-data.ts` — scenarios A/B/C  
- `verdict-readiness.ts` — deterministic readiness  
- `evidence.ts` — filters  
- `storage.ts` — per-project localStorage  
- `selectors.ts` — stages / specialists helpers  

## Storage

Key: `marketsynth.product_alpha.investigation.v1.{projectId}`  

- Survives refresh  
- Does not overwrite intake draft  
- Scenario reset clears and rebuilds workspace  

## Verdict readiness rules

- **not_ready** — critical missing data open, blocking contradiction, or &lt;2 core areas covered  
- **conditionally_ready** — can prepare with warnings / assumptions / gaps  
- **ready_for_review** — core areas covered, no critical blockers  

`notABusinessVerdict: true` always.

## Limitations

- No LLM, web search, live progress, final verdict generation  
- CTA only notifies that Phase A4 owns verdict  

## Checks

```bash
cd web
npx eslint "src/lib/investigation/**/*.{ts,tsx}" "src/components/investigation/**/*.{ts,tsx}" --max-warnings 0
npx --yes tsx src/lib/investigation/verdict-readiness.selfcheck.ts
```

## Future backend

Investigation run entity, source ingestion, evidence CRUD, contradiction resolution workflow, specialist status stream, verdict draft API (A4+).

# Product Alpha Phase A2 — Project Intake & Idea Validation Setup

**Status:** COMPLETED (local)  
**Date:** 2026-07-13  
**Constraints:** Landing visuals frozen · Workspace centerpiece preserved · no backend · no runtime · mock only

## User flow

1. Entry → `/workspace/projects/new` (Project Basics)
2. Product / service → `/workspace/projects/new/idea`
3. Market → `/workspace/projects/new/market`
4. Audience → `/workspace/projects/new/audience`
5. Economics → `/workspace/projects/new/economics`
6. Materials (mock attachments) → `/workspace/projects/new/materials`
7. Review + intake readiness → `/workspace/projects/new/review`
8. **Начать исследование** → local mock project → `/workspace/projects/{id}/investigation`

## Routes

| Path | Step |
|---|---|
| `/workspace/projects/new` | Basics |
| `/workspace/projects/new/idea` | Product |
| `/workspace/projects/new/market` | Market |
| `/workspace/projects/new/audience` | Audience |
| `/workspace/projects/new/economics` | Economics |
| `/workspace/projects/new/materials` | Materials |
| `/workspace/projects/new/review` | Review |
| `/workspace/projects/[projectId]/investigation` | Investigation shell (mock) |

## Entry points

All navigate to the same canonical intake:

- Landing CTA «Проверить мою идею» → `/workspace/projects/new` (href only; visual freeze preserved)
- Workspace Header / Empty hero / Quick Action «Создать проект»

## Draft model

`ProjectIntakeDraft` in `web/src/lib/project-intake/types.ts`

- `projectBasics`, `product`, `market`, `audience`, `economics`, `materials`
- `readiness`, `currentStep`, `updatedAt`
- Persistence: `localStorage` key `marketsynth.product_alpha.intake_draft.v1` via `storage.ts`

## Readiness rules

`evaluateIntakeReadiness` in `readiness.ts` — **not** a business verdict.

- **ready** — critical brief complete; optional gaps / assumptions absent
- **conditionally_ready** — research may start; gaps/assumptions listed
- **insufficient_data** — too vague / missing critical fields

Self-check: `npx --yes tsx src/lib/project-intake/readiness.selfcheck.ts` (from `web/`)

## Temporary limitations

- No backend project create / auth / file upload
- Investigation is queued mock only — no LLM, no live progress animation
- Materials are UI mock records

## Future backend requirements

- Project + IntakeBrief persistence
- Investigation run orchestration
- Specialist status stream for Agency Runtime Monitor
- Real material storage
- Auth-scoped drafts

## Landing / Workspace

- Landing composition unchanged except CTA destination href (`/agents/chat` → `/workspace/projects/new`)
- Agency Runtime Monitor reused on investigation shell (queued specialist mock)
- Browser verification (local): `/` 200 + CTA href; `/workspace` 200 + Agency Runtime Monitor; `/workspace/projects/new` and `/review` 200 (compiled)

## Checks

- eslint on A2 frontend scope: pass
- readiness.selfcheck: pass
- tsc: no errors in A2 scope (pre-existing repo tsc failures unrelated)

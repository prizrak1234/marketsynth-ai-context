# Product Alpha Phase A1 — Workspace Foundation

**Status:** COMPLETED (local)  
**Date:** 2026-07-13  
**Constraints:** Landing frozen · no backend · no runtime · mock UI only

## Route

- **Workspace:** `/workspace`
- **Landing (frozen):** `/` — untouched

## Pages added

| Path | Purpose |
|---|---|
| `/workspace` | Agency command center |
| `/workspace/projects` … `/workspace/settings` | Nav placeholders (A1) |

## Components

- `workspace-page-view.tsx` — composition
- `workspace-header.tsx`, `workspace-nav.tsx`
- `agency-runtime-monitor.tsx` — **demo centerpiece**
- `active-projects.tsx`, `workspace-empty-hero.tsx`
- `investigation-pipeline.tsx`, `recent-verdicts.tsx`, `workspace-quick-actions.tsx`
- `workspace-placeholder.tsx`

## Mocks

`web/src/lib/workspace/mock-data.ts` — projects, specialists, pipeline, verdicts  
Toggle: `MOCK_WORKSPACE_SHOW_EMPTY`

## Temporary

- All actions are local mock notices
- Nav sections beyond Home are placeholders
- No persistence / auth wiring

## Backend needed later

Projects, Investigation runs, Specialist status stream, Verdicts, Knowledge attach, Execution gate — without Chat UI surface.

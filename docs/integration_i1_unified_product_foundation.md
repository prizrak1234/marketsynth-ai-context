# Integration I1 — Unified Product Foundation

**Status:** completed locally (frontend integration only)  
**Checkpoint before I1:** `0524316` — Product Alpha A1–A6 + reconciliation audit  
**Paused:** Product Alpha A7 · AI.592 · Architecture V2.2  

---

## Architectural decision

```
Backend domain / Runtime (Source of Truth)
        ↓
Existing FastAPI services & contracts
        ↓
web/src/lib/integration adapters
        ↓
Marketsynth Workspace (commercial UI)
```

Product Alpha localStorage remains UX/draft/mock — **not** production SoT.

No second Runtime, Control Center, project engine, AgentType set, or MarketingPlan service.

---

## Integration mode

| Mode | Behavior |
|---|---|
| `mock` | Product Alpha demos (default) |
| `backend` | Existing APIs only — honest empty/error/unauthorized/unavailable |
| `hybrid` | Backend where supported; **labelled** mock only for gaps / missing API key |

Config:

- Env: `NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE`
- Override: `localStorage marketsynth.integration.mode.v1`
- Visible label + select on Workspace

**Rule:** API failure never becomes fabricated “research in progress”.

---

## Code delivered

| Area | Path |
|---|---|
| Mode | `web/src/lib/integration/mode.ts` |
| Contracts | `contracts.ts` |
| Errors | `errors.ts` |
| Project adapter | `project-adapter.ts` |
| CC adapter | `control-center-adapter.ts` |
| Monitor loader | `runtime-monitor-adapter.ts` |
| Workspace loader | `load-workspace.ts` |
| Roles | `role-mapping.ts` |
| localStorage registry | `localstorage-registry.ts` |
| Domain mapping | `domain-mapping.ts` |
| Selfcheck | `integration.selfcheck.ts` |
| UI wire | `workspace-page-view.tsx`, `active-projects.tsx`, `agency-runtime-monitor.tsx` |

Backend schema / migrations / routes: **unchanged**.

---

## Workspace ↔ Control Center

| Surface | Responsibility |
|---|---|
| Marketsynth `/workspace` | Project cards, commercial overview, Monitor projection, Alpha journey |
| Campaign Control Center API + `/agents/chat` panel | Campaign operational cockpit (health, next_action, supervisor, timeline) |

Deep link: ` /agents/chat?projectId=&campaignId= `

---

## AI.591

Absent in this checkout. Monitor lists explicit unavailable capabilities (workforce, current_stage, owner role, project timeline, decisions ledger).

---

## Validation run

- `npx tsx src/lib/integration/integration.selfcheck.ts` OK  
- Alpha A4–A6 selfchecks OK  
- eslint touched files OK  
- `pytest tests/test_api_projects.py` OK  
- `pytest tests/test_phase_ai_164_campaign_control_center_regression.py` OK  
- `/workspace` HTTP 200  

---

## Next: I2

Project and Intake Persistence Integration — write path draft → Project + Brief without inventing Investigation/Verdict services yet.

Companion docs:

- [integration_i1_backend_frontend_mapping.md](./integration_i1_backend_frontend_mapping.md)
- [integration_i1_api_support_matrix.md](./integration_i1_api_support_matrix.md)
- [integration_i1_role_mapping.md](./integration_i1_role_mapping.md)
- [integration_i1_localstorage_migration_plan.md](./integration_i1_localstorage_migration_plan.md)
- [product_alpha_ai591_reconciliation_audit.md](./product_alpha_ai591_reconciliation_audit.md)

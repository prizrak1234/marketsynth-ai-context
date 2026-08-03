# Integration I2 — Project + Intake Persistence

**Status:** completed locally (frontend integration)  
**Depends on:** Integration I1  
**Does not start:** A7 · AI.592 · Architecture V2.2 · Investigation backend

## Goal

Connect Product Alpha Project Intake to the existing backend **Project** domain:

- real `project_id` after “Начать исследование” in backend/hybrid modes;
- project appears in Workspace via `GET /projects`;
- **full** `ProductIntakeDraft` remains a local (versioned) draft until a dedicated Brief/Intake domain;
- no second Project model; no schema/migration in I2.

## Baseline (audited)

| Surface | Actual contract |
|---------|-----------------|
| Create | `POST /projects` body: `{ name, description? }` |
| Update | `PATCH /projects/{id}` body: `{ name?, description?, config? }` |
| Response | `id, owner_id, name, description, config, created_at, updated_at` |
| Owner | from auth — never trust frontend owner id |
| Frontend client | `web/src/lib/api/endpoints/projects.ts` — create/fetch/update added in I2 |

## Persist now vs keep local

**Persisted (backend Project):** name; condensed description; optional `config.marketsynth_i2` correlation pointer (draft id + fingerprint + local version) — **not** the full brief.

**Local only:** market, audience, economics, materials, assumptions, missing data, readiness, investigation artifacts.

See [integration_i2_intake_project_field_mapping.md](integration_i2_intake_project_field_mapping.md).

## Integration layer

| Module | Role |
|--------|------|
| `web/src/lib/integration/intake-project-mapping.ts` | Draft → create/update payloads |
| `web/src/lib/integration/project-write-adapter.ts` | Error normalization |
| `web/src/lib/integration/project-sync.ts` | Create/update, lock, reconcile, CTA labels |

## Modes

| Mode | Behavior |
|------|----------|
| mock | Local mock project; no backend calls |
| backend | Real create/update; **no** silent mock fallback |
| hybrid | Real Project core; full intake sections remain local and labelled |

## Flows

1. Validate readiness → fingerprint → create or update → store `backendProjectId` on draft → navigate `/workspace/projects/{id}/investigation`.
2. Investigation remains Product Alpha mock-only (banner states this explicitly).
3. Double-submit blocked in-memory; ambiguous network create does **not** auto-retry POST.

Policy: [integration_i2_sync_and_conflict_policy.md](integration_i2_sync_and_conflict_policy.md).  
Future Brief domain (docs only): [integration_i2_future_project_brief_contract.md](integration_i2_future_project_brief_contract.md).

## Verification

```bash
cd web
npx --yes tsx src/lib/integration/integration.selfcheck.ts
npx --yes tsx src/lib/integration/project-write.selfcheck.ts
npx --yes tsx src/lib/project-intake/readiness.selfcheck.ts
```

## Confirmed gaps (no migration in I2)

- No backend Intake/Brief entity for full questionnaire.
- No attachment storage.
- No Investigation domain API.
- Project API has no create idempotency key — frontend fingerprint + conflict state only.

# Integration I3 — Investigation APIs (actual + future)

## Endpoints used in I3 (no new routes)

| Endpoint | Role in Investigation Workspace |
|----------|----------------------------------|
| `GET /projects/{project_id}` | Load real Project |
| `GET /projects/{project_id}/business-campaigns/search?view=control` | Pick primary campaign |
| `GET .../business-campaigns/{id}/control-center` | Timeline + health projection |
| `GET .../business-campaigns/{id}/supervisor-report` | Quality signals (not evidence) |
| `GET /projects/{project_id}/marketing-skills/runs` | Related skill artifact candidates |

Page load does **not** call execute-specialist, provider dry-run, or publishing.

## Future additive API (documentation only — not implemented in I3)

Preferred pattern after approval:

```
POST   /projects/{project_id}/investigations
GET    /projects/{project_id}/investigations
GET    /projects/{project_id}/investigations/{investigation_id}
PATCH  /projects/{project_id}/investigations/{investigation_id}
```

Child resources only when justified: sources, evidence, findings, missing-data, risks, contradictions.

Minimal aggregate sketch:

```
Investigation {
  id, owner_id, project_id,
  status, version,
  intake_fingerprint,
  project_core_snapshot,  // name/description only
  created_at, updated_at
}
```

Rules:

- owner/project isolation;
- no Business Verdict stored here;
- verdict readiness may be derived field, not GO/NO-GO;
- no hidden chain-of-thought;
- no unvalidated giant JSON brief dump.

## Feature flag (future)

`INVESTIGATION_DOMAIN_ENABLED=false` recommended when tables land.

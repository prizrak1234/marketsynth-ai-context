# Integration I4 — Verdict APIs

## Used now (read-only helpers)

| Endpoint | Role |
|----------|------|
| `GET /projects/{id}` | Project name / existence |
| Campaign list + supervisor-report | Verdict **input signals** only |
| CC summary `next_action_type` | OperationalRecommendation signal |

No `POST/GET …/business-verdicts` in I4.

## Future (Option B — not implemented)

```
POST   /projects/{project_id}/business-verdicts
GET    /projects/{project_id}/business-verdicts
GET    /projects/{project_id}/business-verdicts/{verdict_id}
PATCH  /projects/{project_id}/business-verdicts/{verdict_id}
POST   .../submit-review
POST   .../approve
POST   .../supersede
```

Requirements when added: owner isolation; append-only versions; no strategy/execution side effects; no chain-of-thought; origin + snapshot hash required; approval ≠ execution approval.

# Commercial MVP P0.5 — BusinessVerdict API

## Investigation-scoped

- `POST /projects/{project_id}/investigations/{investigation_id}/business-verdicts`
- `POST /projects/{project_id}/investigations/{investigation_id}/business-verdicts/build-draft`

## Project-scoped

- `GET /projects/{project_id}/business-verdicts` (filters: type, lifecycle, confidence, investigation_id, version, date ranges)
- `GET /projects/{project_id}/business-verdicts/latest`
- `GET /projects/{project_id}/business-verdicts/{verdict_id}`
- `PATCH /projects/{project_id}/business-verdicts/{verdict_id}` (draft only)
- `GET /projects/{project_id}/business-verdicts/{verdict_id}/evidence-snapshot`
- `POST .../submit-review` · `approve` · `reject` · `return-draft` · `supersede` · `archive` · `build-draft`

Auth + owner/project isolation required. No Strategy/Execution side effects. No provider calls.

## Errors (409)

`verdict_type_not_allowed` · `insufficient_evidence` · `unresolved_critical_evidence` · `invalid_transition` · `immutable_verdict` · `stale_version` · `evidence_snapshot_invalid` · `forbidden`

# Commercial MVP P1 — Versioning Matrix

| Domain | Start | Supersede pointer | Unique active rule | Latest resolution | Patch immutable? | History readable? | Parent pin exact? | Floats to newest parent? |
|--------|-------|-------------------|--------------------|-------------------|------------------|-------------------|-------------------|--------------------------|
| ProjectBrief | 1 | `supersedes_brief_id` | unique `(project_id, version)` | `/latest` + max version | submitted: no | yes | n/a | n/a |
| Investigation | 1 | `supersedes_investigation_id` | unique `(project_id, version)`; one active | `/latest` | completed/cancelled/superseded: no | yes | brief id+version+fingerprint | **No** |
| Source | 1 | `supersedes_source_id` | fingerprint uniqueness project-scoped | list / versions endpoints | identity via supersede only | yes | n/a | n/a |
| Evidence | 1 | `supersedes_evidence_id` | per investigation lineage | list/summary | non-draft content: no | yes | source ids same project | **No** (links pin source_id) |
| BusinessVerdict | 1 | `supersedes_verdict_id` | unique `(project_id, version)` | `/latest` | non-draft / approved: no | yes | inv version, brief version, evidence versions + hash | **No** |
| MarketingStrategy | 1 | `supersedes_strategy_id` | unique `(project_id, version)` | `/latest` | non-draft / approved: no | yes | verdict id+version + snapshot hash | **No** |

## Rules verified

- Version starts at 1 for all P0 commercial entities.
- Supersede creates a new row; no cycles enforced by create-on-supersede pointing to known prior id.
- Child objects store **exact** parent versions at write time and do not auto-rebase.
- Rejected/archived/superseded remain readable via get/list.

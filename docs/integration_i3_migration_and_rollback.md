# Integration I3 — Migration and rollback

## I3 schema changes

**None.** No Alembic migration. No new tables. No edits to prior migrations.

## Why

Option B (adapters) satisfied I3 integration goals without durable Investigation SoT. Introducing Source/Evidence tables requires separate approval after I4 decision semantics.

## Local DB drift

Unrelated existing local migration drift (if any) is **out of scope** for I3 — do not “repair” in this phase.

## Rollback

I3 is frontend-only. Rollback = revert frontend integration files / docs. No DB downgrade.

## When Option C migrates later

- Append-only Alembic revision from current head only.
- Indexes on (owner_id, project_id, investigation_id).
- FK to projects consistent with existing conventions.
- Tenant isolation tests mandatory.
- Document upgrade steps in that future phase.

# Integration I4 — Migration and rollback

## Schema changes

**None.** Option C — no Alembic revision, no tables.

## Rationale

Evidence SoT missing (I3). Persisting BusinessVerdict that can be `approved` without durable evidence would fake authority. Local labelled preview is the honest interim.

## Rollback

Revert frontend integration modules + docs. No DB downgrade.

## Future Option B migration notes

Append-only only; indexes `(owner_id, project_id)`; FK to projects; nullable investigation/evidence FKs; no drop/rename; tenant isolation tests; feature flag default off.

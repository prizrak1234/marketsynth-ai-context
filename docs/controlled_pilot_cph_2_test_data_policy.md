# CPH.2 — Test data policy

## Prefix

`E2E-PILOT-{runId}` — used as Project Intake name (`CPH2_RUN_ID` or timestamp).

## Created per run

Project, ProjectBrief, Investigation, Sources, Evidence, BusinessVerdict, MarketingStrategy, ImplementationPlan, MarketingPlan **draft**, handoff record.

## Isolation

- Owned by CPH2 pilot user only.
- Do not reuse manual demo projects.
- Scripts refuse DB name `botfazer`.

## Cleanup

Prefer:

1. Keep disposable pilot DB and drop/recreate schema with bootstrap when needed; or
2. Delete only projects whose name starts with `E2E-PILOT-` via owner-scoped API/admin tooling (not a new production delete endpoint in CPH.2).

Never cascade-delete across owners.

## Artifacts

`web/test-results/cph2-artifactsage/<runId>/lineage.json` stores IDs/versions (no Brief/Evidence text dumps).

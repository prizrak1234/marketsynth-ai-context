# Commercial MVP P0.5 — Evidence Snapshot

## Entity

`BusinessVerdictEvidenceSnapshot`

- exact `evidence_ids` + `evidence_versions`
- `snapshot_hash` (SHA-256 over project/investigation/versions)
- counts: accepted / missing_critical / conflicting_critical / outdated_critical
- `area_coverage`, `readiness_status`, `verdict_readiness_contribution`

## Rules

- Immutable after create
- May reuse hash within same Project + Investigation
- Verdict render must use snapshot, not live Evidence queries as original basis
- Cross-project / cross-investigation Evidence forbidden on links

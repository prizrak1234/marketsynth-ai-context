# CPH.4 — Data integrity checks

## Baseline (pre-backup)

Recorded in `*.baseline.json` / manifest:

- Commercial table row counts
- Firewall table counts (execution / campaign / publication if present)
- Lineage sample IDs/versions/hashes for one full draft handoff chain
- Pilot user IDs + `has_password_hash` flags
- Session active/revoked totals

## Post-restore comparisons

| Check | Failure code |
|-------|----------------|
| Alembic revision = `20260715_0037` | `backup_revision_mismatch` / `restored_revision_unknown` |
| Commercial tables present | `schema_parity_failed` |
| Row counts match manifest | `row_count_mismatch` |
| Lineage IDs/hashes match | `lineage_integrity_failed` |
| No orphan briefs / investigations / source links | `lineage_integrity_failed` |
| No cross-project source links | `lineage_integrity_failed` |
| MarketingPlan status `draft` | `lineage_integrity_failed` |
| Password hashes present; no trivial plaintext | `lineage_integrity_failed` |

## Lineage chain verified

Project → Brief → Investigation → Sources → Evidence → Verdict (`evidence_snapshot_hash`) → Strategy → ImplementationPlan → handoff (`mapping_fingerprint`) → MarketingPlan **draft**

Values must not “float” to a newer unrelated project.

## Verified drill sample (final1)

| Sample | Value (abbreviated) |
|--------|---------------------|
| Project | `be4d7c1b-…` |
| Snapshot hash | `16a37422…` |
| Handoff fingerprint | `d900c33c…` |
| MarketingPlan | `9d697fe3-…` status **draft** |

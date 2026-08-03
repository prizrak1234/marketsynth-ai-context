# CPH.4 — RPO / RTO

## Pilot targets (recommended)

| Metric | Pilot target | Rationale |
|--------|--------------|-----------|
| **RPO** | ≤ 24 hours | Daily full logical dump; not continuous replication |
| **RTO** | ≤ 30 minutes | Local pilot DB is small; restore + validate + smoke |
| Backup frequency | Daily + **before every migration** | |
| Retention | ≥ 7 daily + all pre-migration points for 30 days | |
| Encryption | Disk / volume encryption assumed; no app-level dump encryption yet | |
| Storage | `%USERPROFILE%\botfazer_backups\cph4\` (+ off-machine copy recommended) | |
| Operator | Local pilot operator (developer/admin) | |
| Drill frequency | At least monthly + after auth/schema changes | |

Do **not** claim zero data loss without WAL archiving / PITR / managed continuous backup.

## Measured CPH.4 drill (`final1`, small pilot DB)

| Step | Seconds |
|------|---------|
| Backup (dump+baseline+manifest) | ~0.8 |
| Checksum verify | ~0.1 |
| Create DB + restore | ~1.9 |
| Schema/lineage + session revoke + auth smoke | ~6.8 |
| **Total recovery** | **~10.2** |

These numbers are **not** production-scale performance claims.

## Current RPO exposure

With daily dumps only: up to **~24h** of writes since last backup may be lost.

### Improving RPO later (not in CPH.4)

- More frequent dumps (e.g. every 1–4h)
- WAL archiving + PITR
- Managed PostgreSQL automated backups

## Improving RTO later

- Documented cutover runbook (CPH.5+)
- Warm standby / promote (future)
- Faster checksum tooling for large dumps

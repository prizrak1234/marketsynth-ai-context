# CPH.1 — Data reconciliation plan (`botfazer` → Commercial MVP head)

**Status:** Plan only. **Not executed** against local data DB in CPH.1.  
**Gate:** `reconciliation_requires_owner_approval`

## Precondition

1. Verified backup exists (see backup doc; SHA256 recorded).
2. Owner acknowledges `botfazer` holds AI.60x / ops extras **and lacks** commercial tables.
3. Pilot traffic uses `botfazer_cph1` / `botfazer_pilot`, not the drifted DB.

## Divergence classes

| Difference | Class | Action |
|------------|-------|--------|
| Orphan Alembic `20260608_0033` | destructive / unknown if stamped | Do not stamp; rebuild or leave |
| Missing commercial tables | requires migration path on **empty** lineage | Prefer fresh DB + upgrade head |
| Extra AI.60x tables | manual review | Keep in archive DB or selective export |
| Shared `projects` / `users` / `marketing_plans` | requires data transformation | Selective export with integrity checks |
| Campaign / marketing conveyor rows | manual review | Export if needed for demo continuity |

## Proposed paths (owner picks)

### Path P1 — Leave data DB; use clean pilot (default)

- Precondition: backup done  
- Action: none on `botfazer`  
- Verification: inventory still shows orphan revision  
- Rollback: N/A  
- Risk: low  

### Path P2 — New empty DB + optional selective import

1. Backup + restore dry-run (already proven).  
2. Create `botfazer_pilot`, `alembic upgrade head`.  
3. Dry-run export of `users` / selected `projects` (SQL) without assuming FK completeness.  
4. Import only after column compatibility check.  
5. Count checks + checksum of key IDs.  
6. Cut over `DATABASE_URL`.  
7. Keep `botfazer` renamed/archived.  

Destructive if owners expect AI.60x tables to remain primary.

### Path P3 — In-place repair

**Not recommended.** Orphan revision + missing commercial tables + extra tables ≠ behind-by-N upgrade.

## Checks required before any cutover

- `check-revision` → `current`  
- `schema-parity` → no missing commercial tables  
- Application fail-fast startup succeeds  
- Commercial lineage smoke on that DB  
- Row counts for imported tables  
- Backup of **both** old and new before delete  

## Explicit non-actions in CPH.1

- No `alembic stamp head` on `botfazer`  
- No DROP of `botfazer`  
- No data migration into `botfazer_cph1` beyond incidental test users from smoke  

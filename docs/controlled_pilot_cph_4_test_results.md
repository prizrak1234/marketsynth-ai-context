# CPH.4 — Test results

## Checkpoint

| Item | Value |
|------|-------|
| CPH.3 commit | `f14b70d` `feat: harden pilot authentication and sessions` |
| Branch | `master` (local; no push) |
| Source DB | `botfazer_cph1` |
| Source / code revision | `20260715_0037` |
| Legacy `botfazer` | Not used |

## Verified backup (drill `final1`)

| Field | Value |
|-------|--------|
| backup_id | `cph4_botfazer_cph1_20260715T183230Z` |
| SHA-256 | `8DA24FF4AC4E8352513F73F5AD067B6DBD9CB800190553E66B1D49E87641C698` |
| Size | 385225 bytes |
| Format | PostgreSQL custom (`-Fc`) |
| Location | `%USERPROFILE%\botfazer_backups\cph4\` (outside git) |

## Restore

| Field | Value |
|-------|--------|
| Target | `botfazer_cph4_restore_final1` |
| Restored revision | `20260715_0037` |
| Schema parity | pass |
| Row counts | pass |
| Lineage | pass (MarketingPlan **draft**) |
| Sessions revoked | 22; active after policy = 0 |
| Auth smoke | login + open lineage project + draft MP + write project + logout |
| Execution firewall | pass (no delta on execution/campaign/publication tables) |
| Corrupted backup | rejected (`backup_checksum_failed`) |
| Unsafe targets | rejected |
| Wrong revision manifest | rejected |

## Measured timings (seconds)

| Step | s |
|------|---|
| backup | 0.82 |
| checksum | 0.10 |
| restore | 1.87 |
| verify+smoke | 6.83 |
| total | 10.25 |

## Automated tests

```text
uv run pytest tests/test_controlled_pilot_cph_4_backup_restore.py tests/test_controlled_pilot_cph_3_browser_sessions.py -q
→ 18 passed
```

## Confirmations

- Pilot source DB not destructively modified by restore tooling
- Restored old sessions not trusted
- No MarketingPlan approval, Agent Run, Campaign, execution, publication, provider, or budget action in smoke
- Product Alpha A7, AI.592, Architecture V2.2 remain paused
- No remote git operations

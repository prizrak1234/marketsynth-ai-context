# CPH.4 — Backup manifest

## Purpose

Every pilot backup must have a machine-readable manifest **without secrets**.

## Fields (conceptual `BackupManifest`)

| Field | Notes |
|-------|--------|
| `backup_id` | `cph4_<db>_<UTC>` |
| `source_database` | Must be `botfazer_cph1` |
| `source_host_sanitized` | host:port only |
| `source_revision` | Expected `20260715_0037` |
| `postgres_version` | Truncated `version()` |
| `application_commit` | Short git SHA |
| `created_at` / `completed_at` | ISO UTC |
| `backup_format` | `custom` |
| `filename` | `*.dump` basename |
| `file_size` | Bytes |
| `sha256` | Uppercase hex |
| `table_counts` | Commercial + auth tables |
| `firewall_counts` | Execution-sensitive tables if present |
| `commercial_lineage_sample` | IDs / versions / hashes only |
| `session_policy` | `A_revoke_all_after_restore` |
| `restore_test_status` | `pending` → `passed` |
| `restore_database` | Disposable name after drill |
| `restore_verified_at` | ISO UTC after verify |
| `timings_seconds` | dump / checksum / total |

## Forbidden in manifests

- Passwords, full `DATABASE_URL`, raw session tokens, API keys
- Brief / Evidence / Verdict narrative payloads

## Redacted example

```json
{
  "backup_id": "cph4_botfazer_cph1_20260715T183230Z",
  "source_database": "botfazer_cph1",
  "source_host_sanitized": "localhost:5432",
  "source_revision": "20260715_0037",
  "backup_format": "custom",
  "filename": "cph4_botfazer_cph1_20260715T183230Z.dump",
  "file_size": 385225,
  "sha256": "8DA24FF4AC4E8352513F73F5AD067B6DBD9CB800190553E66B1D49E87641C698",
  "session_policy": "A_revoke_all_after_restore",
  "commercial_lineage_sample": {
    "project_id": "be4d7c1b-…",
    "marketing_plan_status": "draft",
    "evidence_snapshot_hash": "16a37422…"
  }
}
```

Live manifests live **outside** the repo under `%USERPROFILE%\botfazer_backups\cph4\`.

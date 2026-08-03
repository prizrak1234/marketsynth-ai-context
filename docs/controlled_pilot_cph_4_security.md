# CPH.4 — Security notes

## Backup storage

- Files outside git (`botfazer_backups/`, `*.dump` ignored)
- Restrict OS ACLs on the backup directory where possible (Windows: user profile)
- Local disk is **not** off-site: keep a second copy on another machine/volume for pilot resilience
- No cloud object storage integration in CPH.4

## Credentials

- Scripts never print passwords or full DSNs (sanitized `***`)
- `PGPASSWORD` only in subprocess env when needed
- Manifests omit secrets and narrative payloads
- Password hashes restored; plaintext passwords absent

## Sessions

- Restored sessions revoked (Policy A) before use
- Old cookies must not authorize `/auth/me` on restored env
- New login required

## Restore isolation

- Target name gated to `botfazer_cph4_restore_*`
- `CPH4_CONFIRM_RESTORE=1` required for recreate
- Pilot source `botfazer_cph1` and legacy `botfazer` protected
- Cleanup limited to disposable prefix

## Encryption assessment

| Control | Pilot status |
|---------|--------------|
| Encryption at rest | Relies on host/volume encryption |
| Dump file encryption | Not implemented (future) |
| Key management | OS / operator responsibility |
| Transport | Local socket / localhost for drill |

Do not commit dumps or manifests containing sensitive IDs beyond what ops needs; prefer keeping manifests with backups off-repo.

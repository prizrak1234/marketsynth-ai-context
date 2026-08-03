# CPH.4 — Session restore policy

## Decision: Policy A (default)

1. Restore `browser_sessions` rows with the full backup (forensic completeness).
2. Immediately revoke **all** restored sessions (`status=revoked`, `revoked_at=now()`).
3. Do not trust cookies minted before restore.
4. Require a fresh `/auth/login` against the restored database.

## Why not keep sessions active?

Restored token hashes create security ambiguity across environments: a stolen backup or an old browser cookie could appear legitimate after restore.

## Alternatives considered

| Option | Notes |
|--------|--------|
| A — Revoke all after restore | **Selected** |
| B — Exclude sessions from restore | Loses forensic audit trail |
| C — Environment invalidation key | Deferred; more ops complexity |

## Required tests

- `/auth/me` without new login fails after restore
- Login succeeds with restored password hashes
- Logout invalidates the new restored-environment session

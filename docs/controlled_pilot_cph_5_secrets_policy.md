# CPH.5 — Secrets policy

## Inventory

| Secret | Where |
|--------|--------|
| PostgreSQL password | env / Compose |
| Browser session cookie (token entropy) | DB stores hash only |
| Service API keys | server env only |
| Provider keys | disabled for pilot |
| TLS material | Caddy files (not in git) |

## Rules

- No secrets in repository or frontend bundles
- No secrets in logs / manifests
- Separate development vs pilot secrets
- Rotation is a manual operator procedure (replace env + restart; revoke sessions)

No vault platform introduced in CPH.5.

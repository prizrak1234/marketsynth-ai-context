# Commercial MVP P0.5 — Local verdict migration

Key: `marketsynth.product_alpha.verdict.v1.{projectId}`

## Rules

- Do not delete local store
- No auto-upload
- Compare project/investigation/snapshot fingerprint before any conversion
- Explicit conversion → backend `draft`, origin `deterministic_local_import`
- Human review required
- Backend approved remains authoritative
- Conflicts displayed; no silent merge

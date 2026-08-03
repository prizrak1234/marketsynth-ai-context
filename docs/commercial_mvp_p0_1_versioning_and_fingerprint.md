# Commercial MVP P0.1 — Versioning and fingerprint

## Versioning

- First brief = version 1
- Only one open `draft` per project
- Submit makes draft `submitted` and immutable
- Prior `submitted` becomes `superseded`
- Further edits: `POST …/supersede` → new draft version
- History ordered by version desc

## Fingerprint

`compute_project_brief_fingerprint` — SHA-256 of normalized JSON of business content:

- Includes sections + readiness + assumptions/missing
- Excludes ids, timestamps, status, FE sync metadata
- Used for duplicate submitted detection and future Investigation snapshot linkage
- **Not** an auth token

## Money uncertainty

`MoneyValue.mode`: `exact` | `range` | `unknown` — unknown must not coerce to zero.

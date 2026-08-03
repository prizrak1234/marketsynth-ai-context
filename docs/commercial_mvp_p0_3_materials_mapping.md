# Commercial MVP P0.3 — Materials mapping

P0.1 `ProjectBrief.materials_summary` items are **Source registration candidates**, not auto-Sources.

Helper: `app/domain/source_fingerprint.material_to_source_candidate`

Rules:

- user confirmation required
- no binary content
- no automatic URL access
- preserve local_reference_label
- provenance typically `user_provided` / `uploaded`
- `auto_migrate: false`

No page-load migration.

# Commercial MVP P0.3 — Versioning and fingerprint

## Immutability

Registered Source identity fields do not mutate. Material identity change → new version via `supersede` (`supersedes_source_id`, `version++`). Old row → `superseded`.

Allowed without new version: status transitions (archive), reliability review audit.

## Fingerprint

SHA-256 over: `project_id`, `source_type`, normalized URL, publisher, published_at, content_hash, normalized title.

Excludes: reliability, status, notes, timestamps unrelated to identity.

Duplicate live fingerprint in same Project → `duplicate_source` (409).

## SourceSnapshot

Contract fields: source_id, project_id, version, fingerprint, content_hash, captured_at, accessed_at, supersedes_source_id, status.

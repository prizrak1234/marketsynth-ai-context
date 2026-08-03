# Knowledge Storage Model (Phase H2.3)

Durable store: PostgreSQL tables `knowledge_items` and `knowledge_snapshots`.

## Immutability

- One row per `(code, version)`.
- Approved content is **never overwritten in place**.
- Supersede creates a new version row and marks the previous row `superseded`.

## Storage decision

Option A remains: PostgreSQL metadata (+ future FTS).  
`embeddings_enabled = false` in H2.3–H2.5.

## Models

- `KnowledgeItemTable` — content + metadata + tenancy
- `KnowledgeSnapshotTable` — immutable refs attached to UserRequest

Migration: `alembic/versions/20260716_0042_knowledge_storage_user_request_context.py`

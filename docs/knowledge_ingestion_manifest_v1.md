# Knowledge Ingestion Manifest v1 (Phase H2.3)

Explicit curated sources only — **no recursive `/docs`**, no audits, no mocks, no secrets.

Machine list: `INGESTION_MANIFEST_V1` in `app/knowledge_foundation/approved_content_pack.py`.

Each entry records:

- `source_uri` / `source_hash`
- `split_policy` (`atomic_single_item`)
- `knowledge_item_code`
- `target_locale`
- `authority`
- `reviewer`
- `status` (`approved`)
- `reason` / `pack`

API: `GET /knowledge-foundation/policy` → `ingestion_manifest_v1`.

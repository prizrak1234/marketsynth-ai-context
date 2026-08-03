# Knowledge Snapshot Policy (Phase H2.5)

When knowledge is attached to a UserRequest, create an immutable `KnowledgeSnapshot`.

## Fields

id, owner_id, project_id, skill_code/version, capability_pack_version, retrieval_policy_version, locale, item_refs, snapshot_hash, created_at.

## Rules

- Snapshot hash is stable for the same ordered item refs.
- Later supersedes of knowledge **do not** mutate existing snapshots.
- New UserRequests retrieve the latest approved versions.

Implementation: `app/knowledge_foundation/snapshot_service.py`

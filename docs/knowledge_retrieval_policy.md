# Knowledge Retrieval Policy (Phase H2.1)

Deterministic order (no vector similarity as confidence):

1. Constitutional policy  
2. Skill-specific approved knowledge  
3. Owner knowledge  
4. Project knowledge  
5. Approved examples  

## Result fields

Knowledge ID/version, source URI, authority, tenant/project scope, relevance reason, citation requirement.

## Excluded from retrieval

`candidate`, `under_review`, `rejected`, `superseded`, `archived`, `obsolete`, `forbidden`, `historical_record`.

## Storage decision

**Option A — PostgreSQL metadata + full-text search** (`postgres_fts`).  
Embeddings disabled. Vector adapter deferred until semantic retrieval is demonstrably required.

Implementation: `app/knowledge_foundation/retrieval_policy.py`, `storage_decision.py`.

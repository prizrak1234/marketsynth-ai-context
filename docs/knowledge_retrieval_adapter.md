# Knowledge Retrieval Adapter (Phase H2.4)

Deterministic adapter — **no embeddings**, no vector similarity as confidence.

## Input

`KnowledgeRetrievalRequest`: skill_code/version, specialist_role, owner_id, project_id, locale, scopes, query_terms, limit.

## Output

`KnowledgeRetrievalResult`: items, snapshot_hash, retrieval_policy_version, excluded_count, warnings.

Each item includes id/code/version, source, authority, scope, citation_required, relevance_reason, content_hash.

## Order

1. constitutional  
2. skill-specific approved  
3. owner-scoped  
4. project-scoped  
5. approved examples  

Implementation: `app/knowledge_foundation/retrieval_adapter.py`  
Policy version: `1.0`

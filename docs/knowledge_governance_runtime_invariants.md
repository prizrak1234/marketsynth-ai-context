# Knowledge Governance — Runtime Invariants

**Phase:** KG.1 architecture + KG.2 operational enforcement  
**ADR:** [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md)

## Invariants

### KG-I1 — Lifecycle completeness

`KnowledgeGovernanceStatus` MUST include exactly:

`draft`, `validated`, `published`, `deprecated`, `archived`, `superseded`.

Forbidden: `draft → published`, `archived → published`, mutating published version content.

### KG-I2 — Knowledge Object required fields

`KnowledgeObject` MUST declare: knowledge_id, owner, reviewer, review_date, next_review, confidence, freshness, visibility, tenant, domain, evidence_chain, decision_chain, version, status.

Published versions MUST have owner, reviewer, review_date, next_review_at, source_uri, content.

### KG-I3 — Semantic Chunk structure

`SemanticChunk` MUST declare: title, intent, rule, condition, exception, references.  
Arbitrary token-window chunking is not a substitute for this contract.

### KG-I4 — Benchmark case fields

Governed benchmark pack (`drilling_operations`, ≥30 cases) MUST declare: question, expected_source_ids, expected_key_facts, forbidden_claims, requires_expert, minimum_confidence, acceptable_answer_criteria.

### KG-I5 — Validation pipeline order

Stages MUST be: knowledge_candidate → human_review → validation → publication.  
No auto-publish.

### KG-I6 — Citation Contract

`CitationContract` / `CitationRecord` MUST include answer/claim, evidence, source, confidence.  
Missing citation on citation-required skills → Quality Gate block (`citation_missing`).

### KG-I7 — Freshness axes

Freshness: `fresh`, `due_for_review` (≤14 days to next_review), `expired`, `deprecated`, `unknown`.  
Expired MUST be excluded from Runtime Snapshot. Deprecated only for historical analysis. Superseded stores `replacement_version_id`.

### KG-I8 — Governed Snapshot before PromptPackage

Specialist execution for governed-required domains MUST attach an immutable KnowledgeSnapshot with `governance_meta` (version_ids, chunk_ids, source_ids, freshness_summary, policy_decision, hash). Empty/expired → `insufficient_governed_knowledge`.

### KG-I9 — Tenant / visibility before retrieval

Filters apply before fragment selection: tenant_owner_id, visibility, ownership, published status. Never filter secrets after generation.

## Tests

- `tests/test_architecture_knowledge_governance.py`
- `tests/test_phase_kg2_knowledge_governance_ops.py`

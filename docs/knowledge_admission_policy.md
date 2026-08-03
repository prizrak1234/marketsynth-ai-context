# Knowledge Admission Policy (Phase H2.1)

Only **`approved`** knowledge may be used in production specialist work.

## Required metadata (`KnowledgeItem`)

`id`, `title`, `knowledge_type`, `domain`, `specialist_roles`, `source_uri`, `source_hash`, `version`, `status`, `authority`, `tenant_scope`, `project_id` (nullable), `locale`, `valid_from`, `valid_until` (nullable), `supersedes_id` (nullable), `tags`, `citation_required`, `created_at`, `reviewed_at`, `reviewed_by`.

## Statuses

`candidate` → `under_review` → `approved` | `rejected`  
Also: `superseded`, `archived`.

**Governance lifecycle (ADR-KG-001):** Draft → Validated → Published → Deprecated | Archived | Superseded — see [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md) and `KnowledgeGovernanceStatus` in contracts. Legacy statuses remain; mapping is documented in contracts.

## Rules

1. Allowlist sources only — never whole-repo scan.
2. `obsolete` / `forbidden` never admit.
3. `historical_record` is not operational truth.
4. No secrets, credentials, or private chain-of-thought.
5. Tenant / project boundaries enforced on retrieval.
6. Research/strategy factual claims require `citation_required`.
7. Knowledge-backed agent answers must satisfy the Citation Contract (Answer + Evidence + Source + Confidence) once enforcement lands.

Implementation: `app/knowledge_foundation/admission.py`.  
Governance architecture: [knowledge_governance_subsystem.md](knowledge_governance_subsystem.md).

# CORE_CONTRACT_DEFINITIONS_PATCH.md

Apply this patch to `CORE_CONTRACT_DEFINITIONS.md`.

---

# Replace KnowledgeCandidate Contract

Replace the existing KnowledgeCandidate contract with:

```yaml
KnowledgeCandidate:
  id:
  tenant_id:
  project_id:
  outcome_id:
  evidence_id:
  claim:
  scope: session | project | tenant
  status: proposed | validating | promoted | rejected | archived
  validation_result:
  created_at:
  updated_at:
```

# Required Note

Add directly below the contract:

```text
KnowledgeCandidate MUST NOT cross tenant boundary.

Global knowledge is not a KnowledgeCandidate scope.

Global knowledge may only be created through explicit promotion after tenant policy check, validation, anonymization where required, and audit record.
```

# Rationale

The previous value `global_candidate` conflicted with the constitutional invariant that Knowledge Candidate never crosses tenant boundary.

This patch preserves the knowledge promotion model while eliminating unsafe ambiguity.

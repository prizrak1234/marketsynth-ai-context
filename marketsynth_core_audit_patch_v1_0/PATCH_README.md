# PATCH_README.md

**Project:** Marketsynth  
**Patch:** Core Audit Patch v1.0  
**Status:** REQUIRED  
**Purpose:** Fix findings from second independent architecture audit.

---

# Patch Contents

This patch addresses two findings:

1. Critical Knowledge Candidate scope contradiction.
2. Minor Source of Truth hierarchy ambiguity.

---

# Files to update

## 1. `CORE_CONTRACT_DEFINITIONS.md`

Find the `KnowledgeCandidate` contract and replace:

```yaml
scope: session | project | tenant | global_candidate
```

with:

```yaml
scope: session | project | tenant
```

Add this note directly below the contract:

```text
Global knowledge is not a KnowledgeCandidate scope. Global knowledge may only be created through explicit promotion after tenant policy check, validation, anonymization where required, and audit record.
```

## 2. `PROJECT_INDEX.md`

Add the following clarification to the Source of Truth section:

```text
Decision Registry and Project Index are part of the Source of Truth navigation/governance layer, but they do not outrank Constitution, Runtime Invariants, Architecture Core, accepted ADRs/RFCs, or Contracts. They help agents find authority; they do not override authority.
```

## 3. `ARCHITECTURE_CORE.md`

Add the following clarification to the Source of Truth Layer section:

```text
Decision Registry and Project Index belong to the Source of Truth governance/navigation layer. They provide discovery, traceability, and decision indexing. They are lower-priority than Constitution, Runtime Invariants, Architecture Core, accepted ADRs/RFCs, and Contracts.
```

---

# Expected result

After applying this patch:

- Knowledge Candidate remains strictly tenant-safe.
- `global_candidate` cannot be misread as cross-tenant candidate state.
- Source of Truth hierarchy becomes unambiguous.
- The repository can be treated as APPROVED AS SOURCE OF TRUTH pending folder normalization.

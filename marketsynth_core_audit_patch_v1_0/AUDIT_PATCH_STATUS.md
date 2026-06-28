# AUDIT_PATCH_STATUS.md

**Project:** Marketsynth  
**Patch:** Core Audit Patch v1.0  
**Status:** READY TO APPLY  

---

# Findings addressed

## Finding 1 — Critical

KnowledgeCandidate contained `global_candidate` scope.

Resolution:

`global_candidate` removed.

Global knowledge is now explicitly modeled only as promotion output, not candidate scope.

## Finding 2 — Minor

Source of Truth hierarchy ambiguity around Decision Registry and Project Index.

Resolution:

Decision Registry and Project Index are clarified as governance/navigation layer documents below Constitution, Invariants, Architecture Core, ADR/RFC, and Contracts.

---

# Final status after patch

After applying this patch, Marketsynth governance core may be marked:

```text
APPROVED AS SOURCE OF TRUTH
```

Next step:

Repository folder normalization.

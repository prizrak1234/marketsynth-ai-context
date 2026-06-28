# SOURCE_OF_TRUTH_HIERARCHY_PATCH.md

Apply this patch to `PROJECT_INDEX.md` and `ARCHITECTURE_CORE.md`.

---

# Required Clarification

Add this clarification to Source of Truth hierarchy sections:

```text
Decision Registry and Project Index are part of the Source of Truth governance/navigation layer.

They provide discovery, traceability, document routing, and decision indexing.

They do not outrank:

1. PROJECT_CONSTITUTION.md
2. RUNTIME_INVARIANTS.md
3. ARCHITECTURE_CORE.md
4. Accepted ADRs
5. Accepted RFCs
6. Contracts

Project Index helps agents find authority.

Decision Registry records decisions.

Neither document overrides authority.
```

# Rationale

The second independent audit found a minor ambiguity about whether Decision Registry and Project Index are authority sources or navigation/governance helpers.

This patch makes the hierarchy explicit.

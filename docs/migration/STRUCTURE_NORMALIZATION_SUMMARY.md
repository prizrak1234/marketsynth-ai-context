# Structure Normalization Summary

**Date:** 2026-07-13  
**Repository:** marketsynth-ai-context  
**Scope:** File moves only — no document content rewrite, no architecture changes.

---

## Resulting layout

```text
/
  README.md
  PROJECT_CONSTITUTION.md
  PROJECT_INDEX.md
  docs/          (canonical FROZEN + completion/finalization docs)
  archive/
    imported-packs/   (all former root package folders)
```

---

## Canonical documents promoted to root `docs/`

| Destination | Source pack |
|---|---|
| `PROJECT_INDEX.md` (root) | `marketsynth_core_completion_v1_0/` |
| `docs/architecture/ARCHITECTURE_CORE.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/runtime/RUNTIME_INVARIANTS.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/runtime/RUNTIME_MODEL.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/domain/DOMAIN_MODEL.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/engineering/AI_DEVELOPMENT_RULES.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/contracts/CONTRACT_GUIDELINES.md` | `marketsynth_core_architecture_v1_0/` |
| `docs/governance/DOCUMENT_GOVERNANCE.md` | `marketsynth_core_completion_v1_0/` |
| `docs/governance/ADR_RFC_GOVERNANCE.md` | `marketsynth_core_completion_v1_0/` |
| `docs/runtime/APPROVAL_MODEL.md` | `marketsynth_core_completion_v1_0/` |
| `docs/runtime/EXECUTION_MODEL.md` | `marketsynth_core_completion_v1_0/` |
| `docs/knowledge/KNOWLEDGE_MODEL.md` | `marketsynth_core_completion_v1_0/` |
| `docs/security/SECURITY_MODEL.md` | `marketsynth_core_completion_v1_0/` |
| `docs/migration/BOTFAZER_TO_MARKETSYNTH_MIGRATION.md` | `marketsynth_core_completion_v1_0/` |
| `docs/engineering/CURSOR_AUDIT_PLAYBOOK.md` | `marketsynth_core_completion_v1_0/` |
| `docs/api/API_ARCHITECTURE.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/context/CONTEXT_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/contracts/CORE_CONTRACT_DEFINITIONS.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/data/DATA_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/errors/ERROR_HANDLING_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/events/EVENT_ARCHITECTURE.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/integrations/INTEGRATION_ARCHITECTURE.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/memory/MEMORY_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/observability/OBSERVABILITY_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/operations/MULTI_AGENT_COLLABORATION_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/operations/SCALABILITY_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/quality/QUALITY_MODEL.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/testing/TESTING_ARCHITECTURE.md` | `marketsynth_core_finalization_v1_0/` |
| `docs/architecture/SOURCE_OF_TRUTH_HIERARCHY_PATCH.md` | `marketsynth_core_audit_patch_v1_0/` |
| `docs/contracts/CORE_CONTRACT_DEFINITIONS_PATCH.md` | `marketsynth_core_audit_patch_v1_0/` |

Unchanged at root: `PROJECT_CONSTITUTION.md`.

---

## Packages moved to `archive/imported-packs/` (24)

- `marketsynth_core_architecture_v1_0`
- `marketsynth_core_audit_patch_v1_0`
- `marketsynth_core_completion_v1_0`
- `marketsynth_core_finalization_v1_0`
- `marketsynth-ai-context-batch-02`
- `marketsynth-ai-context-starter`
- `marketsynth-ai-governance-index-pack`
- `marketsynth-ai-manifest-pack`
- `marketsynth-ai-operations-manual-pack`
- `marketsynth-ai-specifications-pack`
- `marketsynth-coding-architecture-pack`
- `marketsynth-contracts-pack`
- `marketsynth-developer-standards-pack`
- `marketsynth-development-playbook-pack`
- `marketsynth-domain-architecture-pack`
- `marketsynth-future-domains-pack`
- `marketsynth-governance-pack`
- `marketsynth-knowledge-pack`
- `marketsynth-operations-pack`
- `marketsynth-reference-architecture-pack`
- `marketsynth-reference-library-pack`
- `marketsynth-runtime-pack`
- `marketsynth-system-blueprints-pack`
- `marketsynth-testing-quality-pack`

Nothing was deleted. Full pack trees remain under `archive/imported-packs/` for history.

---

## Link updates

- `README.md` — structure + AI entry points updated to canonical paths.
- `PROJECT_INDEX.md` §5 — repository layout updated to the normalized tree (reading order / authority matrix unchanged).

---

## Not promoted (remain only in archive)

Topic packs (runtime details, contracts catalog, coding guidelines, blueprints, future domains, etc.) were **not** flattened into `docs/` in this pass. They stay in `archive/imported-packs/` until a later selective promotion pass.

---

## Next optional steps

1. Selectively promote ACTIVE docs from archived topic packs into `docs/` by category.
2. Add `docs/adr/` / `docs/rfc/` if ADR/RFC files are extracted from archive.
3. Commit and push this structure normalization.

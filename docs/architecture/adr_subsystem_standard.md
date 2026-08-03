# ADR — Marketsynth Subsystem Standard

**ADR ID:** ADR-SUBSYSTEM-001  
**Status:** Accepted  
**Date:** 2026-07-19  
**Phase:** H2.8E Slice 0  

## Decision

Marketsynth adopts **governed subsystem architecture** for all substantial product capabilities.

Canonical document: [marketsynth_subsystem_standard.md](marketsynth_subsystem_standard.md).

## Context

Product work repeatedly risked becoming:

- isolated service scripts;
- UI checkboxes without operator lifecycle;
- dishonest capability claims;
- silent setup during user requests;
- parallel “mini-runtimes” per feature.

Reviewed integration / RAG materials contributed useful patterns (preflight, immutable index/manifest, ephemeral process/delete, operator runbook, recipes, honest stop conditions) that must live as a **project-wide standard**, not only inside identity generation.

## Rationale

- Prevents isolated feature scripts.
- Preserves **one** Runtime / Agent OS.
- Improves extension to HR, legal, finance, and other future domains.
- Separates **Setup** from **Operation**.
- Makes capability limits explicit.
- Supports auditable execution and maintenance.

## Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| Isolated service per feature without lifecycle | Unmaintainable; no readiness/review/runbook |
| Unrestricted plugin scripts | Breaks security, lineage, and approvals |
| Folder / CLI-driven runtime | Parallel product path; conflicts with Agent OS |
| Parallel agent runtimes | Duplicates registries, approvals, assets |
| Documentation-only standards without invariant tests | Drifts immediately; Slice 0 requires a lightweight invariant test |

## Consequences

- New domains, skills, integrations, and execution paths must be evaluated against the Subsystem Standard **before** implementation.
- Compliance may be `partial` or `missing`; mass refactors are phased, not automatic.
- H2.8E Identity Generation is the first explicit mapping to the standard.
- Paid A/B / diagnostic provider calls remain gated and are **not** part of Slice 0.

## Compliance

See [subsystem_compliance_matrix.md](subsystem_compliance_matrix.md).

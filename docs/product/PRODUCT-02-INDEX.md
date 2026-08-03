# PRODUCT-02 — Index

> **Program:** PRODUCT-02 Commercial Product Blueprint  
> **Status:** **OWNER-FROZEN** (2026-08-02)  
> **`owner_freeze`:** **OWNER-FROZEN**  
> **Decision vocabulary:** OWNER-PROPOSED · OWNER-APPROVED · OWNER-FROZEN · SUPERSEDED

## Document set (seven SoTs)

| # | Document | Owns |
|---|----------|------|
| 1 | [PRODUCT-02-CHARTER.md](./PRODUCT-02-CHARTER.md) | Goals, boundaries, decision statuses |
| 2 | [PROJECT-LIFECYCLE.md](./PROJECT-LIFECYCLE.md) | Project / run / artifact / approval layers |
| 3 | [COMMERCIAL-SPINE.md](./COMMERCIAL-SPINE.md) | Orchestration graph + MVP cut |
| 4 | [CAPABILITY-CATALOG.md](./CAPABILITY-CATALOG.md) | Capability cards + A–F classification |
| 5 | [ARTIFACT-FLOW.md](./ARTIFACT-FLOW.md) | Versioned lineage graph |
| 6 | [TOPOLOGY-DECISIONS.md](./TOPOLOGY-DECISIONS.md) | Project vs Workspace vs Settings |
| 7 | [OWNER-FREEZE.md](./OWNER-FREEZE.md) | Freeze record (owner signed) |

## Related

| Doc | Role |
|-----|------|
| [PRODUCT-02-BLUEPRINT-AUDIT.md](./PRODUCT-02-BLUEPRINT-AUDIT.md) | Consistency audit + PATCH-01 validation |
| [COMMERCIAL_USER_JOURNEY_MAP.md](../COMMERCIAL_USER_JOURNEY_MAP.md) | Journeys |
| [INFORMATION_ARCHITECTURE.md](../INFORMATION_ARCHITECTURE.md) | Screen slots — drift patch with first topology-touching capability |
| Capability Registry | UX exposure only — not authorization |

## Frozen hard rules

1. **Project Command Center** — canonical container for one idea.  
2. Lifecycle = ProjectLifecycleState ≠ CapabilityRunState ≠ ArtifactVersionState ≠ ApprovalRecord.  
3. Launch = subtree; Content ∥ Visuals; Publication multi-instance.  
4. Analytics dual-layer; Optimization post-MVP; Partial Research wall.  
5. Support capabilities ≠ automatic Project stages; MVP spine cut holds.  
6. Capability Registry = UX exposure only — **not** authorization.  
7. Freeze does **not** start Strategy Runtime, Research Hardening, or Slice G.

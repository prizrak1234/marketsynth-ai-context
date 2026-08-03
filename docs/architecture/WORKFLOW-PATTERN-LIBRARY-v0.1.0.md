# Workflow Pattern Library v0.1.0

Frozen read-only knowledge library for Marketsynth Workflow Patterns.

## Status

| Field | Value |
|-------|-------|
| Version | `0.1.0-frozen` |
| Status | `frozen_reviewed_library` |
| Pattern count | 20 |
| Maturity ceiling | `reviewed` |
| Runtime authorized | `false` |
| Production eligible | `false` |

## Tiers

| Tier | Path | Count |
|------|------|-------|
| Pilot | `patterns/pilot/` | 8 |
| Core | `patterns/core/` | 12 |

## Artifacts

| File | Purpose |
|------|---------|
| `library_index.json` | Read-only catalog of all patterns |
| `library_freeze_manifest.json` | Deterministic freeze bundle |
| `source_overlap_matrix.json` | Multi-pattern source overlap audit |
| `pilot_freeze_manifest.json` | Frozen pilot tier reference |
| `core_freeze_manifest.json` | Frozen core tier reference |

## Upstream lineage (immutable)

| Upstream | Hash |
|----------|------|
| WPL schema bundle | `db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25` |
| Workflow catalog | `5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa` |
| Pilot bundle | `d2c3f64171bae91fe84708146ab05ff3fde3941f7645abcb006ca9de74a1a284` |
| Core bundle | `b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf` |

## Consumption rules

Patterns may be referenced by Skills, Discovery, and platform-adaptation planning.
Patterns do **not** grant execution, deployment, Connector, or publication permission.
Green schema tests do not prove runtime correctness.

**KB-WPL-01.4 consumers:** `ms.skill.n8n_workflow_architecture`, `ms.skill.n8n_workflow_debugging`,
`ms.skill.n8n_deployment_review` — read-only pattern/practice references only.

**KB-WPL-01.5 consumer:** `ms.skill.knowledge_linking` — metadata linking across Skills, Patterns,
Practices, RFCs, and indexes.

**KB-WPL-01.6 consumer:** `ms.skill.presentation_architecture` — read-only pattern references for
evidence-grounded generation and quality gates; specification output only (no rendering).

## Related

- [Pattern catalog](./WORKFLOW-PATTERN-CATALOG.md)
- [Extraction methodology](./WORKFLOW-PATTERN-EXTRACTION-METHODOLOGY.md)
- [KB-WPL-01.3C RFC](../rfc/KB-WPL-01.3C-WORKFLOW-PATTERN-LIBRARY-FREEZE.md)
- [KB-WPL-01.4 RFC](../rfc/KB-WPL-01.4-N8N-ENGINEERING-KNOWLEDGE-SKILLS.md)
- [Engineering Skill Matrix](../skills/ENGINEERING-SKILL-MATRIX.md)

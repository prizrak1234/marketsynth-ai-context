# Knowledge packages

Shared schema bundles consumed by native Skills.

| Bundle | Path | Status |
|--------|------|--------|
| Customer Intelligence (CIM) | `customer_intelligence/0.1.0/` | Frozen |
| Marketing Claims | `marketing_claims/0.1.0/` | Frozen (ARCHIVE-MKT-01.1) |
| External Artifacts | `external_artifacts/0.1.0/` | Frozen (KB-SKILL-01.1) |
| Workflow Patterns | `workflow_patterns/0.1.0/` | **Frozen (KB-WPL-01.3C)** |
| Workflow Catalog (metadata) | `workflow_catalog/0.1.0/` | **Frozen (KB-WPL-01.2)** |
| Workflow Pattern Library | `workflow_patterns/0.1.0/` | **frozen_reviewed_library (KB-WPL-01.3C)** |
| Workflow Pattern Pilot | `workflow_patterns/0.1.0/patterns/pilot/` | **Frozen (KB-WPL-01.3A.1)** |
| Workflow Pattern Core | `workflow_patterns/0.1.0/patterns/core/` | **Frozen (KB-WPL-01.3B)** |
| Capability Model | `capability_model/0.1.0/` | **Mapped read-only (KB-WPL-01.7)** |
| Discovery Read Models | `discovery/0.1.0/` | **Read-only discovery (KB-WPL-01.8)** |
| KB-WPL Program | `kb_wpl_program/0.1.0/` | **Integrated freeze (KB-WPL-01.9)** |

**KB-WPL-01.4 consumers** (read-only): `ms.skill.n8n_workflow_architecture`, `ms.skill.n8n_workflow_debugging`, `ms.skill.n8n_deployment_review` — see [Engineering Skill Matrix](../../docs/skills/ENGINEERING-SKILL-MATRIX.md).

**KB-WPL-01.5 consumer** (read-only): `ms.skill.knowledge_linking` — metadata linking across Skills, Patterns, Practices, RFCs, and indexes.

**KB-WPL-01.6 consumer** (read-only): `ms.skill.presentation_architecture` — pattern references for evidence-grounded presentation specification; no rendering.

**KB-WPL-01.7 consumer:** `packages/knowledge/capability_model/0.1.0/` — Profession → Capability → Skill → Pattern → Connector → Tool mapping (read-only).

**KB-WPL-01.8 consumer:** `packages/knowledge/discovery/0.1.0/` — deterministic alias catalog, ranking weights, query modes, fixtures (read-only discovery).

**KB-WPL-01.9 integrated program:** `packages/knowledge/kb_wpl_program/0.1.0/` — program-wide freeze manifest, invariants, hash registry (frozen read-only knowledge program).

**Legacy note:** `app/knowledge/knowledge_linking/` is authoritative for KB-WPL-01.5; `app/knowledge/linking/` is legacy (no new imports).

**Marketing Claims** canonical URI: `https://schemas.marketsynth.ai/marketing-claims/0.1.0/` (identity only — no HTTP resolution).

**External Artifacts** canonical URI: `https://schemas.marketsynth.ai/external-artifacts/0.1.0/`

**Workflow Patterns** canonical URI: `https://schemas.marketsynth.ai/workflow-patterns/0.1.0/`

**Capability Model** canonical URI: `https://schemas.marketsynth.ai/capability-model/0.1.0/`

Bundle hashes (frozen / generated):

- Marketing Claims: `c29ca2c08ccbb8861206fcc855e966c93d50b68264d8d9bdd096e13cd5c32f8d`
- External Artifacts: `cb89298f766d101f0e4c928d720f1f99b52e95c67ac5af48924726ee39e486d2`
- Workflow Patterns: `db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25`
- Workflow Catalog: `5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa`
- Workflow Pattern Pilot: `d2c3f64171bae91fe84708146ab05ff3fde3941f7645abcb006ca9de74a1a284`
- Workflow Pattern Core: `b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf`
- Workflow Pattern Library: `1ddd0d033f6028bd5dcf5ee555186c6be0389a96459615b6221348783d9b1883`
- Capability Model: `e1e2bbeb025a3348944a5dab43e5661d31e2ac559e9e8de4989836c50831e42b`
- Discovery Read Models: `9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8`
- KB-WPL Program (integrated): `43e2cab328dec889ee7fe755bf208311522baec1dd761ef4bb9eac73a53aa4a4`

## Future (KB-02–KB-06)

- KB-02: Knowledge Core persistence
- KB-03: Workflow Pattern Adaptation
- KB-04: Internal n8n Template Generator
- KB-05: Controlled n8n Deployment Gateway
- KB-06: Knowledge-assisted Skill Discovery

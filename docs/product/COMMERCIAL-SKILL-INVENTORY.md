# Commercial Skill Inventory

**Audit:** PRODUCT-00  
**Authority:** Package on disk (`packages/skills/`) — not capability bindings or docs.

## Summary

| Category | On disk | Runtime in `app/` | Frozen | UI path |
|----------|---------|-------------------|--------|---------|
| Commercial marketing (11) | ✅ | ❌ | Partial hashes only | ❌ |
| Engineering (3) | ✅ | ❌ | KB-WPL candidate | ❌ |
| Knowledge linking (1) | ✅ | ❌ | frozen_candidate | ❌ |
| Deferred capabilities | ❌ no package | — | — | — |

---

## Required commercial skills — audit table

| Skill ID | Package | Version | Package hash | Manifest status | Executable | Schemas | Semantic tests | Registry projection | Runtime | UI | Commercial status |
|----------|---------|---------|--------------|-----------------|------------|---------|----------------|---------------------|---------|-----|-------------------|
| `ms.skill.product_marketing_context` | ✅ | 0.1.0 | `5e3dfc1bfc48c56d…cc230` | candidate | false | ✅ | ✅ 12 test files | ✅ validate + project | ❌ | ❌ | contract_only |
| `ms.skill.market_research` | ✅ | 0.1.0 | `6acce32a4952de75…fc14e` | candidate | false | ✅ | ✅ 9 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.competitor_analysis` | ✅ | 0.1.0 | `14903c8744b57c47…8cde0` | candidate | false | ✅ | ✅ 6 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.icp_segmentation` | ✅ | 0.1.0 | `075a4f1989a90506…e71a` | candidate | false | ✅ | ✅ 6 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.market_validation` | ✅ | 0.1.0 (+ **0.2.0** subdir) | root `6c53b5b9…8133`; **frozen 0.2.0** `ec7c86ce…68f7a` | candidate | false | ✅ both versions | ✅ 25 files | ✅ | ❌ package loader | ⚠️ BIV separate | contract_only / BIV parallel |
| `ms.skill.positioning` | ✅ | 0.1.0 | `cbd8283f4addaa9c…e8da6` (**frozen hash**) | candidate | false | ✅ | ✅ 11 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.customer_interview_design` | ✅ | 0.1.0 | `e9e3b3f213e04e8a…e8f2` | candidate | false | ✅ | ✅ 3 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.customer_meaning_extraction` | ✅ | 0.1.0 | `acc0082a88d867f3…771` | candidate | false | ✅ | ✅ 3 files | ✅ | ❌ | ❌ | contract_only |
| `ms.skill.claim_substantiation` | ✅ | 0.1.0 | `faad9e2f23e1cc31…83b4` | candidate | false | ✅ | ✅ 3 files | ✅ | ❌ | ❌ | contract_only |
| **`ms.skill.offer_builder`** | ✅ | 0.1.0 | `b637c3920066953f…02f4` | candidate | false | ✅ | ✅ `test_skill_02_8` + fixtures | ✅ | **❌ zero `app/` refs** | ❌ | **contract_only — key gap** |
| `ms.skill.presentation_architecture` | ✅ | 0.1.0 | `60ce698336fa2100…2e95c` | candidate (KB-WPL frozen_candidate) | false | ✅ | ✅ 5 files | ✅ | ❌ | ❌ | contract_only |

---

## Not on disk (deferred / missing)

| Capability / future skill | Capability model | Package | Notes |
|---------------------------|------------------|---------|-------|
| Content Strategy | `marketing.content_strategy` — **deferred** | ❌ | Gap gap-001 |
| Copywriting | `marketing.copywriting` — **deferred** | ❌ | Gap gap-002 |
| Launch Strategy | `marketing.launch_strategy` — **deferred** | ❌ | Gap gap-003 |
| Visual Brief | deliverables gap | ❌ | No package |
| Telegram content skill | — | ❌ | Distribution via `marketing.distribution` gap |
| YouTube content skill | `deliverables.content_architecture` partial | ❌ | Presentation/content deliverables only |

---

## Non-commercial packages (context)

| Skill ID | Purpose | Commercial relevance |
|----------|---------|---------------------|
| `ms.skill.n8n_workflow_*` (×3) | Engineering KB-WPL | Not product track |
| `ms.skill.knowledge_linking` | Metadata linking | Not customer journey |

---

## Key finding: offer_builder

**Physically exists** — contradicts “not created” but confirms “not integrated”:

```
packages/skills/ms.skill.offer_builder/
├── manifest.yaml          status: candidate, executable: false
├── schemas/input.schema.json, output.schema.json
├── tests/fixtures/        output_proceed_preferred.json, mv_stop_blocked.json, …
└── quality_threshold: skeleton_only
```

Capability model binds `marketing.offer_architecture` → `ms.skill.offer_builder` with `implementation_status: implemented_non_executable`.

**Gap:** package contract ready; no operator/runtime service; Launch Pack does not invoke it.

---

## Hash registry (commercial)

Full hashes recorded in PRODUCT-00 audit run (2026-07-24). Frozen references:

- Positioning: `cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6`
- Market Validation 0.2.0: `ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a`
- Offer Builder: `b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4`

No hash drift detected during PRODUCT-00 audit.

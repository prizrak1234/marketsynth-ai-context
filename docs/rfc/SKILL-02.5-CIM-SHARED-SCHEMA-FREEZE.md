# SKILL-02.5 — CIM Shared Schema Freeze

| Field | Value |
|-------|-------|
| **Phase** | SKILL-02.5 |
| **Status** | **Frozen** |
| **Date** | 2026-07-23 |
| **CIM version** | 0.1.0 |

---

## 1. Executive decision

Customer Intelligence Model (CIM) is promoted from package-local ICP draft schema to a **versioned shared contract** at:

`packages/knowledge/customer_intelligence/0.1.0/`

Canonical URI namespace: `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/`

**ICP produces CIM → shared schema defines contract → downstream Skills consume it.**

`output_contract_type: intelligence` is **not** introduced. ICP remains `research`; CIM is an embedded shared artifact.

---

## 2. Shared schema location

```
packages/knowledge/customer_intelligence/0.1.0/
├── customer-intelligence.schema.json
├── customer-segment.schema.json
├── customer-claim.schema.json
├── job-to-be-done.schema.json
├── decision-role.schema.json
├── priority-assessment.schema.json
├── segment-conflict.schema.json
├── provenance.schema.json
├── icp-local-compatibility.json
├── freeze_manifest.json
├── README.md
└── consumers/
```

---

## 3. Canonical URI namespace

| Schema | URI |
|--------|-----|
| CIM root | `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/customer-intelligence.schema.json` |
| Segment | `.../customer-segment.schema.json` |
| Claim | `.../customer-claim.schema.json` |
| JTBD | `.../job-to-be-done.schema.json` |
| Decision role | `.../decision-role.schema.json` |
| Priority | `.../priority-assessment.schema.json` |
| Conflict | `.../segment-conflict.schema.json` |
| Provenance | `.../provenance.schema.json` |

URI is identifier only — no network resolution.

---

## 4. Version policy

- **Frozen:** CIM `0.1.0` immutable after this audit
- Breaking change → next major (e.g. `1.0.0`)
- Additive compatible change → `0.2.0` during pre-1.0 stage
- No unversioned `latest` URI
- Package version ≠ CIM version (separate identities)

---

## 5. Producer/consumer model

| Role | Entity |
|------|--------|
| Producer | `ms.skill.icp_segmentation` v0.1.0 |
| Shared contract | CIM v0.1.0 bundle |
| Consumers | Positioning, Offer Builder, Content, Copy, CRM, Advertising, MV 0.2.0 |

---

## 6. ICP compatibility strategy

**Strategy A (chosen):** Preserve frozen ICP 0.1.0 unchanged (`075a4f19…ae71a`).

- Local draft: `cim_version: 0.1.0-draft`, package-local schema
- Shared validation via `normalize_icp_local_cim()` → `0.1.0`
- No ICP 0.1.1 required for freeze

---

## 7. Shared schemas

Eight JSON Schema Draft 2020-12 files preserving SKILL-02.4 field domains. Forbidden top-level: verdict, positioning, final_offer, execution_status.

---

## 8. Consumer boundaries

Documented in [CIM-consumer-contracts-v0.1.0.md](../knowledge/CIM-consumer-contracts-v0.1.0.md).

Conceptual fixtures in `consumers/` for Positioning, Offer, Content, Copy, CRM, Advertising, Market Validation 0.2.0.

---

## 9. Positioning invariant

> Positioning is a CIM consumer, not a segmentation engine.

---

## 10. Offer invariant

Offer Builder consumes CIM pains/outcomes/objections/triggers — does not redefine customer model.

---

## 11. Content/Copy invariant

Content and Copywriting reference explicit `selected_segment_ids` — no silent audience expansion.

---

## 12. CRM boundary

CRM handoff maps segment intelligence to qualification fields. No personal records in CIM.

---

## 13. Market Validation boundary

MV 0.2.0 consumes CIM priority/evidence/blockers; retains viability verdict authority.

---

## 14. MKG mapping

Frozen logically in [CIM-MKG-mapping-v0.1.0.md](../knowledge/CIM-MKG-mapping-v0.1.0.md). No graph persistence.

---

## 15. Compatibility policy

Statuses: `compatible`, `conditionally_compatible`, `incompatible`, `unknown`.

Implemented in `app/knowledge/cim_compatibility.py`. No automatic migrations.

---

## 16. Hashes

| Artifact | SHA-256 |
|----------|---------|
| Bundle | `b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea` |
| customer-intelligence.schema.json | `523f4e4844e2620f9ce1c09777c26e1e71ce832c53577e00efcb993a24fdd7e5` |

Full file hashes in `freeze_manifest.json`.

---

## 17. Accepted limitations

- No runtime loader, persistence, API, UI, MCP
- Local registry only (`app/knowledge/cim_schema_registry.py`)
- ICP package-local draft schema remains for frozen hash integrity

---

## 18. Non-goals

Market Validation 0.2.0, Positioning, Offer Builder, Content, CRM, Advertising implementation — deferred to SKILL-02.6+.

---

## 19. Freeze verdict

**ACCEPTED** — single canonical CIM v0.1.0 shared contract; ICP compatibility preserved; all frozen package hashes unchanged; 604 tests green.

---

## Regression

```bash
uv run pytest (Get-ChildItem tests -Filter "test_skill_0*.py").FullName -q
```

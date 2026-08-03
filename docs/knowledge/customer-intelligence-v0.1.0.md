# Customer Intelligence Model — shared contract v0.1.0

**Status:** frozen  
**Bundle path:** `packages/knowledge/customer_intelligence/0.1.0/`  
**Canonical URI:** `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/`

---

## What CIM is

Customer Intelligence Model (CIM) is the **single authoritative contract** for evidence-aware customer intelligence: ranked segments, ICP candidates, JTBD, pains, outcomes, triggers, barriers, objections, roles, trust drivers, conflicts, and unknowns.

CIM describes **segment-level buyer intelligence**, not individual CRM contacts or personal data.

---

## Producer

| Skill | Version | Role |
|-------|---------|------|
| `ms.skill.icp_segmentation` | 0.1.0 (frozen) | Primary CIM producer |

ICP output contract remains `research`. CIM is embedded as `customer_intelligence` — not a separate output taxonomy value.

---

## ICP 0.1.0 compatibility

Frozen ICP package uses local draft schema (`cim_version: 0.1.0-draft`). Shared validation uses:

```python
from app.knowledge.cim_compatibility import normalize_icp_local_cim, validate_icp_local_against_shared
validate_icp_local_against_shared(local_cim_document)
```

Mapping: [icp-local-compatibility.json](../../packages/knowledge/customer_intelligence/0.1.0/icp-local-compatibility.json)

---

## Schema files

| File | Purpose |
|------|---------|
| `customer-intelligence.schema.json` | Root document |
| `customer-segment.schema.json` | Segment record |
| `customer-claim.schema.json` | Pain/outcome/trigger/barrier/objection/trust |
| `job-to-be-done.schema.json` | JTBD |
| `decision-role.schema.json` | Buying roles |
| `priority-assessment.schema.json` | Explainable priority |
| `segment-conflict.schema.json` | Conflicts |
| `provenance.schema.json` | Provenance stub |
| `freeze_manifest.json` | Hashes and metadata |

---

## Local resolution

```python
from app.knowledge.cim_schema_registry import validate_canonical_document
validate_canonical_document("0.1.0", "customer-intelligence.schema.json", doc)
```

No HTTP fetch. URI is identifier only.

---

## Forbidden in CIM

- Commercial viability verdict
- Positioning statements
- Final offers
- Campaign / execution status
- Personal customer records

---

## Related

- [CIM consumer contracts](CIM-consumer-contracts-v0.1.0.md)
- [CIM ↔ MKG mapping](CIM-MKG-mapping-v0.1.0.md)
- [SKILL-02.5 freeze RFC](../rfc/SKILL-02.5-CIM-SHARED-SCHEMA-FREEZE.md)

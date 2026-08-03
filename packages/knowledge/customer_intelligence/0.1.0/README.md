# Customer Intelligence Model — shared schema bundle v0.1.0

**Status:** frozen  
**Canonical URI base:** `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/`

This directory is the **single authoritative CIM contract** for downstream Skills and Knowledge Core consumers.

## Files

| File | Purpose |
|------|---------|
| `customer-intelligence.schema.json` | Root CIM document |
| `customer-segment.schema.json` | Segment record |
| `customer-claim.schema.json` | Pain/outcome/trigger/barrier/objection/trust |
| `job-to-be-done.schema.json` | JTBD record |
| `decision-role.schema.json` | Buying roles |
| `priority-assessment.schema.json` | Explainable segment priority |
| `segment-conflict.schema.json` | Segment conflict record |
| `provenance.schema.json` | Provenance stub |
| `freeze_manifest.json` | Hashes and freeze metadata |
| `icp-local-compatibility.json` | ICP 0.1.0 local → shared mapping |

## Producer

Primary producer: `ms.skill.icp_segmentation` v0.1.0 (frozen package-local draft schema).

ICP package hash remains unchanged; use `normalize_icp_local_cim()` before shared validation.

## Non-goals

No persistence, graph DB, runtime loader, or network schema fetch.

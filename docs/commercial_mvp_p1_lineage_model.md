# Commercial MVP P1 — Canonical Lineage Model

```
Project
  └─ ProjectBrief (version N, input_fingerprint)
       └─ Investigation (version M, project_brief_id + project_brief_version + input_fingerprint)
            ├─ InvestigationSourceLink → Source (version S, fingerprint, project-scoped)
            └─ Evidence (version E, input_fingerprint, EvidenceSourceLink → Source)
                 └─ Evidence Snapshot (snapshot_id + evidence_snapshot_hash)
                      └─ BusinessVerdict (version V, pins brief/inv versions + snapshot)
                           └─ MarketingStrategy (version W, pins verdict id+version + snapshot hash)
```

MarketingPlan / Campaign / AgentRun / ExecutionApproval are **not** children of this chain.

## Edge dictionary

| Edge | Reference fields | Version/hash | Ownership | Immutability | Parent lifecycle | Parent superseded | Child exists |
|------|------------------|--------------|-----------|--------------|------------------|-------------------|--------------|
| Project → Brief | `project_id`, `owner_id` | `version` unique per project | project owner | submitted+ immutable content | any | new Brief version via supersede | multiple versions OK |
| Brief → Investigation | `project_brief_id`, `project_brief_version`, `input_fingerprint` | inv `version` | same project+owner | completed/cancelled/superseded immutable | **submitted** only | new Investigation must pin new Brief version | one active inv enforced |
| Investigation → Source (link) | `investigation_id`, `source_id`, scoped project/owner | Source has own `version` | same project | Source identity via supersede only | not cancelled required at attach | links remain; Source may be superseded | unique (inv, source) |
| Source → Evidence (via links) | `source_id` in EvidenceSourceLink | Evidence `version`; excerpt_hash | same project + investigation | non-draft Evidence content immutable | registered/available preferred | superseded Source blocked for new Evidence | Evidence creates new row on supersede |
| Evidence → Snapshot | snapshot rows + `business_verdict_evidence_links.evidence_version` | `evidence_snapshot_hash` | same investigation | snapshot immutable after create | accepted Evidence included | live Evidence change does **not** rewrite snapshot | Verdict owns snapshot |
| Snapshot → Verdict | `evidence_snapshot_id`, `evidence_snapshot_hash`, inv/brief version pins | Verdict `version` | same project | approved Verdict immutable | GO rules need inv under_review/completed | supersede creates new Verdict version | drafts may coexist under rules |
| Verdict → Strategy | `business_verdict_id`, `business_verdict_version`, type, snapshot hash copy | Strategy `version` | same project | approved Strategy immutable | **approved** + GO/CONDITIONAL_GO | Strategy keeps pinned Verdict version | build-draft allowed per eligibility |

## Required questions (verified)

1. **Investigation ↔ Brief:** only submitted — `brief_not_submitted`.
2. **Evidence ↔ Source:** same project — `cross_project_source`.
3. **Verdict ↔ Evidence:** exact versions + hash — `stale_version` on mismatch at write.
4. **Strategy ↔ Verdict:** approved GO/CONDITIONAL_GO only.
5. **Evidence after Verdict:** cannot rewrite approved Verdict basis (snapshot pin).
6. **Verdict after Strategy:** cannot rewrite approved Strategy (verdict version pin + Strategy immutability).

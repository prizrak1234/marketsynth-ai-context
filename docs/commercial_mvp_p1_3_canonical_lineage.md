# P1.3 Canonical Lineage

```
Project
→ ProjectBrief (id, version, input_fingerprint)
→ Investigation (id, version, brief_id/version/fingerprint)
→ Source (id, version) + InvestigationSourceLink
→ InvestigationEvidence (id, version, fingerprint) + EvidenceSourceLink (source_id/version)
→ BusinessVerdictEvidenceSnapshot (hash) + VerdictEvidenceLink
→ BusinessVerdict (id, version, snapshot hash, brief/investigation pins)
→ MarketingStrategy (id, version, verdict_id/version, snapshot hash)
→ ImplementationPlan (id, version, strategy_id/version, verdict pins, snapshot hash)
→ ImplementationMarketingPlanHandoff (id, mapping_version, mapping_fingerprint, plan_id/version)
→ MarketingPlan (id, version, status=draft, project_context lineage)
```

## Invariants

- Create paths pin exact parent versions (no float to “latest” on write).
- `/latest` is a read convenience; children retain historical pins after parent supersede.
- Completed handoff cannot reinterpret payload under a newer mapping version without a new fingerprint.
- Handoff confirm creates only MarketingPlan draft.

# P1.3 Handoff Audit

## Confirmed

- Preview creates no MarketingPlan
- Confirm requires `explicit_confirmation=true`
- Created plan `status=draft`
- Fingerprint idempotent; repeated confirm → `idempotent_replay`
- Stale fingerprint rejected
- Unsupported roles excluded; dependency degradation visible
- Approved MarketingPlans never overwritten by handoff
- Lineage in handoff row + MarketingPlan.project_context
- Firewall: no AgentRun / Campaign / execution run / LLM on confirm

## Mapping version

`implementation_to_marketing_plan.v1` — old completed handoffs keep their fingerprint and mapping_version.

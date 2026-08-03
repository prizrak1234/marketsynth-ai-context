# Integration I5 — Future MarketingStrategy domain (docs only)

Not implemented. No migration.

```
MarketingStrategy {
  id, owner_id, project_id,
  verdict_reference,
  investigation_snapshot_reference,
  version, status,
  objectives, segments, positioning, offers,
  channels, funnel, budget_policy, metrics,
  conditions, risks, assumptions,
  supersedes_strategy_id,
  created_at, updated_at
}
```

Rules: no chain-of-thought; no execution authorization; no campaign creation side effect.  
Link to MarketingPlan is explicit handoff (I6), not silent dual-write.

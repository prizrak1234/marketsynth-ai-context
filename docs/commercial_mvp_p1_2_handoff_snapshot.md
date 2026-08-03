# P1.2 Handoff snapshot

Table: `implementation_marketing_plan_handoffs`

Statuses: preview → confirmed → completed | failed | superseded | cancelled

Immutable preview payload after confirmation. Completed handoff cannot create a second MarketingPlan for the same mapping fingerprint (idempotent return).

Lineage also stored in MarketingPlan.project_context under bounded keys (`handoff_id`, `source_implementation_plan_*`, `mapping_*`).

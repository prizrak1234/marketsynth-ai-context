# Capability Gap Register

**Phase:** KB-WPL-01.7  
**Source:** `packages/knowledge/capability_model/0.1.0/capability_gaps.json`

Gaps are explicit — nothing hidden. Mapping does not grant permissions.

## Blocking gaps (sample)

| gap_id | capability | gap_type | impact |
|--------|------------|----------|--------|
| gap-runtime-global | engineering.deployment_review | missing_runtime | Deployment activation blocked until Connector Gateway |
| gap-* (distribution) | marketing.distribution | missing_connector | Publication connector not available |
| gap-* (publication_handoff) | deliverables.publication_handoff | missing_connector | Renderer/publication handoff deferred |

## Deferred marketing capabilities

content_strategy, copywriting, launch_strategy, distribution, marketing_analytics, learning_and_feedback — all `capability_not_released` or `missing_connector`.

## Discovery readiness (KB-WPL-01.8)

Future Discovery will consume this register to explain:

```
User task → Profession → Capability → Skill → Pattern → missing Connector/Tool → blockers
```

No runtime execution in 01.7 or 01.8 read models.

# P1.3 Versioning and Immutability

## Versioning

- First durable version = 1 for Brief / Investigation / Source / Evidence / Verdict / Strategy / ImplementationPlan / MarketingPlan.
- Next version deterministic via repository `next_version` / supersede paths.
- Parent pins: `*_id` + `*_version` (+ fingerprints/hashes where defined).
- Handoff: `mapping_version=implementation_to_marketing_plan.v1` + `mapping_fingerprint`.

## Immutability enforced

- Submitted Brief; accepted Evidence; approved Verdict/Strategy/ImplementationPlan; completed handoff snapshot.
- PATCH on immutable states returns 409 (`immutable_*`).

## Residual

- MarketingPlan remains separately approvable via ops API after handoff creates draft — intentional boundary (handoff ≠ approve).

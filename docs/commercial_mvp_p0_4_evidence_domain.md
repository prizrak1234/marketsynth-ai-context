# Commercial MVP P0.4 — Evidence Domain

## Outcome

Durable **Evidence** = atomic reviewable claims linked to exact Source versions. Lifecycle ≠ assessment. Not Business Verdict / Finding / LLM / supervisor.

## Inventory (not Evidence)

| Artifact | Reuse as Evidence? |
|----------|-------------------|
| LLMResponse | No |
| Supervisor findings | No (quality signals only) |
| MarketingSkillRun | No |
| Source metadata | Provenance only |
| ProjectBrief demand_evidence | Candidate text only |

## Model

`investigation_evidence` + `evidence_source_links` (stance supports/contradicts/context).

Missing Evidence may have zero Sources; all others require ≥1 Source.

## Docs

See sibling `commercial_mvp_p0_4_*.md` files.

## Tests

`uv run pytest tests/test_commercial_mvp_p0_4_evidence.py -q`

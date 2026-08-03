# Discovery Ranking Model

**Phase:** KB-WPL-01.8  
**Bundle:** `packages/knowledge/discovery/0.1.0/ranking_weights.json`

## Principles

1. **Deterministic** — same inputs → same order and hash
2. **Explainable** — every candidate exposes `ranking_factors`, `penalties`, `ranking_explanation`
3. **No hidden scores** — numeric weights visible in bundle
4. **Stable under source reorder** — input order of source records does not affect output

## Required factors

| Factor | Role |
|--------|------|
| `profession_fit` | Profession alignment |
| `capability_fit` | Primary match strength |
| `explicit_request_fit` | Boost for exact ID/capability request |
| `skill_availability` | Boost when Skill package exists |
| `pattern_support` | Lower weight for Pattern-only support |
| `trust_status` | Governed trust tier |
| `maturity` | Review maturity |
| `tenant_visibility` | Visibility-safe candidate |
| `provider_fit` | Provider constraint match |
| `platform_fit` | Platform constraint match (e.g. n8n) |
| `evidence_fit` | Required evidence classes present |
| `approval_compatibility` | Approval constraint compatibility |
| `execution_sensitivity_compatibility` | Penalty for billing/destructive |
| `gap_severity` | Penalty/boost for gap records |
| `dependency_completeness` | Dependency chain completeness |
| `source_quality` | Source bundle quality tier |
| `version_compatibility` | Version alignment |
| `limitations_penalty` | Penalty when limitations present |

## Match strength by type

| match_type | Typical strength | Max confidence |
|------------|------------------|----------------|
| `exact_id` | 1.0 | high |
| `declared_binding` | 0.9 | high |
| `alias` | 0.75 | medium |
| `platform_constraint` | 0.65 | medium |
| `provider_constraint` | 0.6 | medium |
| `exact_token` | 0.55 | low/medium |
| `gap_relation` | 0.85 | medium |

Similarity-only (`exact_token`, alias-only) matches **cannot** reach high confidence.

## Semantic rules

1. Exact capability request outranks alias-only match
2. Existing Skill outranks Workflow Pattern for methodology recommendation
3. Pattern cannot hide missing Skill gap
4. Billing/destructive queries → deny-by-default blockers
5. Profession-only match does not claim implementation readiness

## Result hash

`result_hash` computed from semantic subset excluding `generated_at`. Stable across repeated runs.

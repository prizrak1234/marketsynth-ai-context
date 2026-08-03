# Integration I6 — Semantics matrix

Source of truth for code matrix: `IMPLEMENTATION_SEMANTICS_MATRIX` in
`web/src/lib/integration/implementation-marketing-plan-mapping.ts`.

| Capability | MarketingStrategy | ImplementationPlan | Backend MarketingPlan | Relationship | Source of Truth |
|------------|-------------------|--------------------|-----------------------|--------------|-----------------|
| strategic objective | objectives / summary | overview.strategicObjective | goal (free text) | partial_match | split — plan goal is ops only |
| workstream | n/a | workstreams[] | absent | absent | local ImplementationPlan |
| milestone | n/a | milestones[] | absent | absent | local ImplementationPlan |
| task | n/a | PlanTask (PM item) | specialist_tasks | lower_level | split — different semantics |
| specialist assignment | n/a | responsibleRole | specialist enum | partial_match | subset via ROLE_MAPPINGS |
| dependency | n/a | PlanDependency graph | absent | incompatible | local ImplementationPlan |
| deliverable | n/a | deliverables + acceptance | expected_output text | partial_match | lossy |
| acceptance criteria | n/a | acceptanceCriteria | text append only | partial_match | local authoritative |
| budget range / gate | budget policy | budgetPlan + gates | absent | absent | local ImplementationPlan |
| approval gate | n/a | approvalGates[] local | POST …/approve | incompatible | never collapse |
| condition / risk / assumption | yes | yes | absent | absent | Strategy / Impl local |
| roadmap | n/a | roadmap[] | absent | frontend_only | local |
| readiness | strategy readiness | PlanningReadiness | draft\|approved\|archived | incompatible | never equate |
| version | local | local | MarketingPlanVersion | partial_match | link only |
| approval | local | local review | resource approve | incompatible | per approval boundary |
| execution handoff | blocked | A7 paused | execution-runs (separate) | lower_level | execution services |

**Hard equals:** none. `implementationPlanEqualsMarketingPlan() === false`.

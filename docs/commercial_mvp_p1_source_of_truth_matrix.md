# Commercial MVP P1 — Source of Truth Matrix

| Domain object | Source of Truth | Mutable states | Immutable states | Version owner | Frontend representation |
|---------------|-----------------|----------------|------------------|---------------|-------------------------|
| Project | Backend DB | name/description (owner) | id, owner_id | n/a (identity) | Workspace project list |
| ProjectBrief | Backend `project_briefs` | draft | submitted, superseded, archived (content) | project-scoped `version` | Intake — adapters; local draft may preview until sync |
| Investigation | Backend `investigations` | draft/ready/active/blocked/under_review (stage + fields) | completed, cancelled, superseded | project-scoped `version` | Investigation workspace |
| Source | Backend `sources` | status/reliability via review; no in-place identity edit | superseded, archived identity; content via supersede | project-scoped `version` + fingerprint | Sources panel; backend mode no mock fallback |
| Evidence | Backend `investigation_evidence` | draft content; limited assessment paths | accepted/rejected/superseded/archived **content** | investigation lineage `version` | Evidence panel / summary |
| BusinessVerdict | Backend `business_verdicts` | draft | under_review content locked; approved/rejected/superseded/archived | project-scoped `version` + snapshot | Verdict workspace — durable in backend mode |
| MarketingStrategy | Backend `marketing_strategies` | draft | approved/rejected/superseded/archived | project-scoped `version` + verdict pin | Strategy workspace — durable in backend mode |
| MarketingPlan | Backend ops spine (separate) | draft/specialist tasks per existing rules | approved plan gates | plan version (ops) | Ops panel only — **not** Strategy |
| Runtime Monitor | Derived Control Center | n/a | n/a | n/a | Projection — not commercial SoT |
| Product Alpha local previews | localStorage / mock | yes (labelled) | never override backend in backend mode | local keys | Explicit origin labels; no silent merge |

## Non-shared ownership rules

- Brief/Investigation/Source/Evidence/Verdict/Strategy: **backend owns durable facts**.
- Product Alpha local keys are **preview / migration** only.
- MarketingPlan never shares identity with MarketingStrategy.
- ImplementationPlan (today): **local SoT** until P1.1 — see ImplementationPlan decision.

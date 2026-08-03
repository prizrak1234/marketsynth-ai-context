# P1.3 Source of Truth Matrix

| Object | Source of Truth | Mutable | Immutable | Version authority | Frontend role |
|--------|-----------------|---------|-----------|-------------------|---------------|
| Project | Backend `projects` | name/meta | identity | n/a | Workspace shell |
| ProjectBrief | Backend briefs | draft | submitted+ | project-scoped version | Intake adapter |
| Investigation | Backend investigations | non-terminal | completed/superseded/cancelled | version | Investigation UI |
| Source | Backend sources | supersede/archive paths | superseded/archived identity | version | Source panel |
| Evidence | Backend evidence | draft | accepted+ | version + fingerprint | Evidence trail |
| EvidenceSnapshot | Verdict snapshot table | never | always | hash | Verdict support |
| BusinessVerdict | Backend verdicts | draft | approved+ | version | Verdict workspace |
| MarketingStrategy | Backend strategies | draft | approved+ | version | Strategy workspace |
| ImplementationPlan | Backend impl plans | draft | approved+ | version | Implementation workspace |
| Handoff | `implementation_marketing_plan_handoffs` | preview | confirmed/completed | mapping_version + fingerprint | Handoff panel |
| MarketingPlan | Backend marketing_plans | draft content under ops rules | approved | current_version_number | Ops/related panel |
| AgentRun | Backend agent runs | runtime | historical | run id | Runtime monitor |
| Approvals | Domain-specific gates | pending | decided | per-domain | Never auto from commercial chain |
| Runtime Monitor | Compose of ops APIs | n/a | n/a | n/a | Hybrid may label mock gaps |
| Product Alpha local preview | localStorage | local only | n/a | local version | Explicit mock/hybrid label |

Authority for composed UI is **per field from the owning domain**, never a collapsed shared SoT.

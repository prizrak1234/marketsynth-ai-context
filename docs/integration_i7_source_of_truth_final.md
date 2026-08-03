# Integration I7 — Final Source of Truth matrix

Authority is **per object / field class**. UI may compose views; it must not merge authority.

| Object | Classification | Authority notes |
|--------|----------------|-----------------|
| Project | **backend SoT** | `owner_id` scoped; GET/POST/PATCH |
| Intake Draft | **local SoT** | Full draft in localStorage; partial map → Project name/description (+ config pointer) |
| Investigation | **derived + local** | Backend: Project/CC/Supervisor/skill projections. Alpha workspace local. No Investigation entity |
| Source | **absent / mock** | Future domain. Skill runs ≠ Source |
| Evidence | **absent / mock** | Future domain. Supervisor ≠ Evidence |
| Finding | **derived / local** | Supervisor findings = quality signals; Investigation Finding = local mock |
| Risk | **derived / local** | Not durable Investigation Risk |
| Contradiction | **mock-only / local** | Absent backend |
| Verdict Readiness | **local / derived** | FE engine; ≠ Business Verdict type |
| Business Verdict | **local SoT** | Labelled deterministic preview until Evidence + Verdict domain |
| MarketingStrategy | **local SoT** | GTM; ≠ MarketingPlan |
| ImplementationPlan | **local SoT** | Delivery plan; future domain optional |
| MarketingPlan | **backend SoT** | Specialist-task ops spine |
| Specialist Task | **backend SoT** | On MarketingPlan |
| Agent Run | **backend SoT** | Separate execution record |
| Approval Decision | **split categories** | Never flatten without discriminator (`approval-boundary.ts`) |
| Execution Approval | **backend (gated)** | REAL_EXECUTION expansion; not Alpha path |
| Publication Approval | **backend (publishing)** | Separate from MarketingPlan approve |
| Campaign Control Center | **backend SoT** | Campaign ops panel |
| Runtime Monitor | **derived** | Projection of CC — not a second Runtime engine |
| Timeline | **derived (CC)** | Investigation timeline projection |
| Recommended Next Step | **derived** | CC `next_action` / Supervisor — **not** Verdict |

## Hard non-equalities

Project ≠ Intake Draft · Investigation ≠ Agent Run · Source ≠ LLM · Evidence ≠ Supervisor · Verdict Readiness ≠ Business Verdict · Business Verdict ≠ Approval · MarketingStrategy ≠ MarketingPlan · ImplementationPlan ≠ MarketingPlan · Impl Task ≠ Specialist Task · Specialist Task ≠ Agent Run · MarketingPlan approve ≠ Execution approve · Execution approve ≠ Publication approve · Campaign readiness ≠ Business viability

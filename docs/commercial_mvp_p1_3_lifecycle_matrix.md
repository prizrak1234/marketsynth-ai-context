# P1.3 Lifecycle Matrix (summary)

| Domain | Key transitions | Auto-creates child? |
|--------|-----------------|---------------------|
| ProjectBrief | draft → submitted | no Investigation |
| Investigation | draft → active → … | no AgentRun |
| Source | register → attach | no Evidence |
| Evidence | draft → review → accepted | no Verdict |
| BusinessVerdict | draft → review → approved | no Strategy |
| MarketingStrategy | draft → review → approved | no ImplementationPlan |
| ImplementationPlan | draft → review → approved | no Handoff / MarketingPlan |
| Handoff | preview → confirmed → completed | **MarketingPlan draft only** on confirm |
| MarketingPlan | draft → approved (ops) | no execution on create |

Critical: every commercial approve steps **eligibility**, not automatic downstream construction (except explicit handoff confirm → draft).

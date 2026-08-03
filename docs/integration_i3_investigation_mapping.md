# Integration I3 — Investigation capability & stage mapping

## Capability matrix

| Product Alpha capability | Existing backend | Match | Source of Truth | Adapter | Backend gap |
|--------------------------|------------------|-------|-----------------|---------|-------------|
| Investigation status | Campaign health / none | derived | **Frontend view** (`InvestigationViewStatus`) | `investigation-status-adapter` | Investigation aggregate |
| Investigation pipeline (9 stages) | Marketing plan tasks / CC timeline | incompatible ontology | **Frontend projection** | `investigation-adapter` stageProjections | Stage run entity |
| Sources | Skill runs, tools, LLM | partial / incompatible | **absent** | `source-adapter` → artifact **candidates** only | InvestigationSource |
| Evidence | — | absent | **absent** | `evidence-adapter` firewall | InvestigationEvidence |
| Findings | Supervisor findings | incompatible | campaign quality only | quality signals | InvestigationFinding |
| Missing Data | Supervisor missing_inputs / brief | partial strings | campaign | quality signals | InvestigationMissingData |
| Contradictions | Supervisor strings / critic JSON | partial | campaign | quality signals | InvestigationContradiction |
| Risks | Supervisor risks / strategist | partial | campaign | quality signals | InvestigationRisk |
| Opportunities | research draft sections | absent/weak | — | none | Investigation opportunity |
| Assumptions | intake local / brief | partial | local + campaign | I2 draft | Brief domain |
| Specialist activity | CC + specialist outputs | partial | campaign/plan | I1 monitor | workforce overlay |
| Verdict readiness | FE formula only | derived FE | **frontend-only** | verdict-readiness.ts | do not use CC readiness |
| Timeline | CC timeline | partial | campaign ops | investigation-adapter | Investigation event log |
| Version/snapshot | — | absent | — | intake fingerprint (local) | Investigation version |
| Project intake reference | Project + local draft | partial | Project core + local | I2 linkage | ProjectBrief |

Match values: exact | partial | derived | incompatible | absent

## Stage mapping (UI projections)

| Stage | Backend input | Completion condition | Blocker | Real / derived / mock |
|-------|---------------|----------------------|---------|------------------------|
| Project Context | `GET /projects/{id}` | Project exists | 404/auth | **real** |
| Market Research | skill `metrica_analysis` etc. | never auto-complete | no Evidence | derived hint `needs_review` if run exists |
| Competitor Analysis | — | — | absent | mock / not_started |
| Audience Analysis | `segment_research` | skill ≠ done | absent | derived hint |
| Demand Signals | `wordstat_research` | skill ≠ done | absent | derived hint |
| Economics | — | — | absent | not_started |
| Risk Assessment | Supervisor risk strings | quality ≠ RiskItem | absent Risk entity | derived needs_review |
| Evidence Review | — | Evidence SoT absent | **blocked** | derived blocked |
| Verdict Preparation | — | I4 | no verdict API | not_started |

No fake progress percentages.

## Status mapping

Backend campaign health → `InvestigationViewStatus` (display only).  
Product Alpha `InvestigationStatus` strings may appear as labels but are **not** persisted backend enums.

## Agent Run / Task inclusion

**Include:** MarketingSkillRun in `INVESTIGATION_RELATED_SKILL_TYPES`; primary campaign CC + supervisor.  
**Exclude:** unrelated AgentRuns; publishing package runs; LLMRequest as Source/Evidence; arbitrary Tasks; execution/approval readiness as verdict readiness.

# Integration I3 — Source and Evidence model

## Semantic chain (required)

```
Source → extracted fact → Evidence item → Finding → Risk/Opportunity → Verdict readiness
```

Agent / Supervisor / LLM output may **propose** a finding, but is **not** confirmed Evidence without Source + review.

## Source model decision (I3)

| Need | Backend today | Decision |
|------|---------------|----------|
| Durable Source identity | absent | **gap** — design only |
| Skill / tool runs | MarketingSkillRun, tool calls | Map as **research_artifact_candidate** with origin=backend |
| LLM payloads | llm_requests/responses | **Forbidden** as Source |

Candidate future `InvestigationSource` fields (not implemented):

- id, owner_id, project_id, investigation_id
- title, source_type, origin_uri_ref (not full blob)
- accessed_at, freshness, reliability, status
- content_ref / checksum
- citation_key

## Evidence model decision (I3)

| Need | Backend today | Decision |
|------|---------------|----------|
| EvidenceItem graph | absent (`EvidenceRecord` marked absent in V2.1 map) | **SoT absent** |
| Supervisor Finding | campaign QA | **Quality signal only** — never auto Evidence |
| Specialist JSON | desk research | may seed draft Finding later — not Evidence |

Evidence states remain Product Alpha UI: confirmed | partial | conflicting | missing | outdated.

## Findings / Risks / Missing / Contradictions

| Object | I3 treatment |
|--------|----------------|
| CampaignSupervisorFinding | `campaign_quality_finding` |
| missing_inputs[] | `campaign_missing_input` (string) |
| contradictions[] | `campaign_contradiction_string` |
| risks[] | `campaign_risk_string` |
| Product Alpha MissingDataItem / RiskItem / ContradictionItem | mock (hybrid/mock) or empty (backend) until domain approved |

## Firewall tests

`investigation.selfcheck.ts` asserts Supervisor mapping never yields EvidenceItem shape and skill runs use `research_artifact_candidate` role.

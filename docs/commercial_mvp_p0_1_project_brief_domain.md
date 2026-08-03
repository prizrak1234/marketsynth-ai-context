# Commercial MVP P0.1 — ProjectBrief domain

**Status:** Implemented locally.

## Boundary

| Entity | Role |
|--------|------|
| **Project** | Identity, owner, name, description, config |
| **ProjectBrief** | Durable versioned structured commercial intake |
| **CampaignBrief** | Separate operator campaign questionnaire — **not** dual-written |

ProjectBrief is **not** stored in `Project.config`.

## Entity

`project_briefs` table with typed JSON sections validated via Pydantic contracts:

`project_basics`, `product`, `market`, `audience`, `economics`, `materials_summary`, `assumptions`, `missing_data`, readiness, fingerprint, version, status.

Statuses: `draft` | `submitted` | `superseded` | `archived`  
Readiness: `ready` | `conditionally_ready` | `insufficient_data` (≠ Business Verdict)

## Side-effect firewall

Create/update/submit/supersede **do not** create Investigation, Agent Run, Verdict, Strategy, Campaign, or execution.

## Next

P0.2 Investigation aggregate linked to `ProjectBrief` id/version.

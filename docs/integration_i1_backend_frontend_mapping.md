# Integration I1 — Backend ↔ Frontend Mapping

## Project card

| Workspace field | Backend source | Transform | Fallback |
|---|---|---|---|
| project ID | `Project.id` | passthrough | — |
| project name | `Project.name` | passthrough | — |
| project status / statusLabel | *(absent on Project)* | fixed label `Backend project` | no Alpha pipeline invented |
| current stage | *(absent)* | — | `Недоступно` |
| last update | `Project.updated_at` | `toLocaleString(ru-RU)` | `Недоступно` |
| next recommended step | `CampaignControlCenterSummary.next_action_type` | underscores → spaces | `Недоступно` |
| active campaign count | summaries with status active/draft | count | `null` → UI `Недоступно` if not fetched |
| control center href | first campaign id | `/agents/chat?projectId&campaignId` | omit link |
| origin | adapter | `backend` \| `mock` | |

Adapter: `web/src/lib/integration/project-adapter.ts`

## Agency Runtime Monitor ← Campaign Control Center

| Monitor field | CC source | Notes |
|---|---|---|
| healthLabel / progress | `health.status`, `progress_percent` | factual |
| nextAction* | `next_action` | factual |
| supervisor score / findings | supervisor_* + `top_findings` | factual |
| metricsSummary | `metrics` totals | factual |
| specialist rows | **derived** from health/next/supervisor/workflow | not AI.591 workforce |
| unavailableCapabilities | static AI.591 gap list | honest |
| badgeLabel | mode-dependent | mock vs CC live read |

**Not mapped (absent):** workforce overlay, current_owner_role, project-wide decisions/timeline, specialist progress board.

## Domain model classes (no tables in I1)

See `web/src/lib/integration/domain-mapping.ts`.

| Model | Class |
|---|---|
| ProjectIntakeDraft | C — Project + Brief |
| InvestigationWorkspace | D — additive |
| BusinessVerdict | D — additive (+ `VerdictKind`) |
| MarketingStrategy | D — additive |
| ImplementationPlan | B — partial ↔ MarketingPlan |
| WorkspaceSnapshot / Monitor | E / B — view / adapter |

# Integration I1 — Role Mapping

Source: `web/src/lib/integration/role-mapping.ts`

**Hard rule:** no new `AgentType` values in I1. Frozen list remains 10 types.

| Product Alpha role | AgentType | Specialist | Kind |
|---|---|---|---|
| CEO | — | — | aggregate UI (owner/governance) |
| Client Owner | — | — | aggregate UI (`owner_id`) |
| Research Director | orchestrator | researcher | frontend alias |
| Market Analyst | analyst | analyst | frontend alias |
| Competitor Analyst | analyst | researcher | frontend alias |
| Audience Analyst | analyst | researcher | frontend alias |
| Risk Officer | critic | critic | frontend alias |
| Chief Marketing Strategist | strategist | strategist | exact match |
| Performance Marketer | — | ad_creative_strategist | frontend alias |
| Content Strategist | content_planner | content_planner | exact match |
| Copywriter | copywriter | copywriter | exact match |
| Designer | media | — | frontend alias |
| Analyst | analyst | analyst | exact match |
| Project Manager | orchestrator | — | frontend alias |

UI agency titles remain presentation / RACI labels unless later product decides additive workforce (not I1).

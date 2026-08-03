# Specialist route mapping (Phase H1)

H1 stores **aliases** on `UserRequest.assigned_specialist` — presentation/routing hints only.

Does **not** create new `AgentType` values and does **not** start AgentRuns.

| Route category | assigned_specialist | Suggested later AgentType |
|----------------|---------------------|---------------------------|
| content, social_media, youtube | content_specialist | copywriter / content_planner via marketing path |
| content_plan | content_planner | content_planner |
| telegram_bot, website, saas, automation | programmer | programmer |
| idea_validation, market_research, competitor_analysis | researcher | researcher (after Project) |
| marketing_strategy | strategist | strategist |

UI labels: `specialist.*` in i18n dictionaries.

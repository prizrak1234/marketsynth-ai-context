# Commercial MVP P0.2 — Investigation Domain

## Outcome

Durable, owner/project-scoped **Investigation** linked to an **exact submitted ProjectBrief** (id + version + fingerprint). Lifecycle and stages are backend SoT. No Source/Evidence persistence, no auto Agent Run / LLM.

## Boundary

| Entity | Role |
|--------|------|
| Project | Identity |
| ProjectBrief | Structured intake snapshot |
| Investigation | Controlled research lifecycle for one Project + one Brief version |

Investigation is **not** Project, Agent Run, Campaign, MarketingPlan, Business Verdict, Source, or Evidence.

## Model (minimal)

`id`, `owner_id`, `project_id`, `project_brief_id`, `project_brief_version`, `input_fingerprint`, `version`, `status`, `current_stage`, `stages`, `readiness_status`, `readiness_reasons`, `started_at`, `completed_at`, `blocked_reason`, `supersedes_investigation_id`, bounded `metadata`, timestamps.

## Product Alpha mapping

| Product Alpha field | Backend Investigation | Persist now | Derived | Future |
|---------------------|----------------------|-------------|---------|--------|
| pipeline stages | `stages` + `current_stage` | yes | — | — |
| investigation status (UX) | `status` mapped to view status | yes | view map | — |
| verdict readiness | `readiness_*` (not Business Verdict) | yes | deterministic | Source/Evidence later |
| sources[] | — | no | — | P0.3 |
| evidence[] | — | no | — | P0.4 |
| findings / risks (mock) | local preview only | no | — | later |
| localStorage workspace | link meta + artifacts | local only | — | — |

## Confirmations

- Page GET does not create/start Investigation.
- Create/start do not trigger Agent Run, LLM, providers, Source, Evidence, Verdict, Strategy.
- Mock mode unchanged; backend mode has no silent mock fallback for Evidence/Source.
- A7, AI.592, Architecture V2.2 remain paused.

## Docs

- [API](commercial_mvp_p0_2_investigation_api.md)
- [Lifecycle & stages](commercial_mvp_p0_2_lifecycle_and_stages.md)
- [Brief linkage](commercial_mvp_p0_2_brief_linkage.md)
- [Frontend](commercial_mvp_p0_2_frontend_integration.md)
- [Migration](commercial_mvp_p0_2_migration_and_rollback.md)

## Tests

`uv run pytest tests/test_commercial_mvp_p0_2_investigation.py -q`

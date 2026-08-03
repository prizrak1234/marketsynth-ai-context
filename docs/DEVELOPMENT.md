# Development rules

## For humans and Cursor

1. **Never start with agent code** — extend contracts and API first.
2. **Evaluate against the Subsystem Standard** — [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md). New domains, skills, integrations, and execution paths must pass the checklist before implementation. A working service/API alone is not complete.
3. **No hardcoded secrets** — use `.env` and `Settings`.
4. **No PII in logs** — use `sanitize_text_for_logs` / structlog processors.
5. **One feature per PR** — keep diffs small and testable.
6. **Setup ≠ Operation** — no silent credential/migration repair during ordinary product requests.
7. **Run before commit:**
    ```bash
    uv run ruff check app tests
    uv run mypy app
    uv run pytest
    ```

Architecture SoT: [architecture/README.md](architecture/README.md) · ADR [architecture/adr_subsystem_standard.md](architecture/adr_subsystem_standard.md) · Compliance [architecture/subsystem_compliance_matrix.md](architecture/subsystem_compliance_matrix.md).

Invariant: `uv run pytest tests/test_architecture_subsystem_standard.py -q`.

## Module boundaries

| Path | Responsibility |
|------|----------------|
| `app/api/` | HTTP only — thin handlers |
| `app/schemas/` | Pydantic contracts |
| `app/domain/` | Business rules |
| `app/services/` | External systems (LLM, Telegram, Redis) |
| `app/identity_generation/` | Identity subsystem (H2.8E) — not a second Runtime |
| `app/db/` | Persistence |
| `app/core/` | Config, logging, security |

## Marketing conveyor (AI.27–AI.39, frozen)

Roadmap: [phase_ai_34_38_marketing_pipeline_roadmap.md](phase_ai_34_38_marketing_pipeline_roadmap.md).  
Readiness audit / freeze gate: [phase_ai_39_marketing_pipeline_readiness_audit.md](phase_ai_39_marketing_pipeline_readiness_audit.md).  
**AI.40+** is a separate branch (`ContentAsset` conversion) — do not extend the frozen pipeline without explicit phase request.

## Marketing department v2 (AI.110–AI.125, frozen at AI.119)

Baseline **14 roles** (frozen six + eight v2 executables). V2 deps in `V2_SPECIALIST_DEPENDENCIES` — separate from frozen matrix.  
Roadmap: [phase_ai_110_marketing_department_v2_roadmap.md](phase_ai_110_marketing_department_v2_roadmap.md).  
Freeze: [phase_ai_119_marketing_department_v2_freeze.md](phase_ai_119_marketing_department_v2_freeze.md).  
Regression: `uv run pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q`.  
Optional demo: `uv run python scripts/seed_e2e_demo.py --include-v2-marketing`.

## Product Scenario Builder (AI.126–AI.135)

Five business scenarios (restaurant, dental leads, blogger content, SaaS launch, local promo) compose specialists into draft plans — no new agents or execution paths.  
Roadmap: [phase_ai_126_scenario_roadmap.md](phase_ai_126_scenario_roadmap.md).  
Audit: [phase_ai_135_scenario_builder_readiness_audit.md](phase_ai_135_scenario_builder_readiness_audit.md).  
Create plan: `POST /projects/{id}/marketing-scenarios/{scenario_id}/create-plan` (draft only; approve + execution run use existing endpoints).  
Regression: `uv run pytest tests/test_phase_ai_134_scenario_builder_regression.py -q`.  
Optional seed: `uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen`.

## Scenario Auto-Run Wizard (AI.136–AI.145)

Manual step wizard over existing approve → execute → asset → package → dry-run job APIs. One step per `POST .../scenario-wizard-runs/{id}/advance` — no background worker.  
Roadmap: [phase_ai_136_scenario_wizard_roadmap.md](phase_ai_136_scenario_wizard_roadmap.md).  
Audit: [phase_ai_145_scenario_wizard_readiness_audit.md](phase_ai_145_scenario_wizard_readiness_audit.md).  
Regression: `uv run pytest tests/test_phase_ai_144_scenario_wizard_regression.py -q`.  
Optional seed: `uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen`.

## Media generation (AI.56–AI.59, frozen)

Roadmap: [phase_ai_56_59_media_generation_layer_roadmap.md](phase_ai_56_59_media_generation_layer_roadmap.md).  
Audit: [phase_ai_59_media_generation_readiness_audit.md](phase_ai_59_media_generation_readiness_audit.md).  
Generation starts only from **approved MediaBrief** via `MediaGenerationJob` — not from chat or `ContentAsset`.  
Default provider is **mock**; OpenAI Images requires `MEDIA_GENERATION_ENABLED` and `OPENAI_IMAGES_ENABLED`.  
**AI.60+** publishing is a separate branch.

## Publishing foundation (AI.60–AI.65, frozen)

Audit: [phase_ai_65_publishing_foundation_readiness_audit.md](phase_ai_65_publishing_foundation_readiness_audit.md).  
Jobs start only from **approved PublicationPackage** + **active** foundation channel. Dry-run only — no external platform APIs.

## Publishing reliability (AI.66–AI.69, frozen)

Audit: [phase_ai_69_publishing_reliability_readiness_audit.md](phase_ai_69_publishing_reliability_readiness_audit.md).  
Optional `Idempotency-Key` on job create (hashed). Replay from `failed`/`cancelled` only. `snapshot_hash` verified on start/execute.

## Telegram publishing (AI.70–AI.75, frozen)

Audit: [phase_ai_75_telegram_publishing_readiness_audit.md](phase_ai_75_telegram_publishing_readiness_audit.md).  
Real send: `POST .../publication-package-jobs/{id}/execute` (Telegram only, `TELEGRAM_PUBLISHING_ENABLED` + `TELEGRAM_BOT_TOKEN`).

## Publishing scheduler (AI.76–AI.79, frozen)

Audit: [phase_ai_79_publishing_scheduler_readiness_audit.md](phase_ai_79_publishing_scheduler_readiness_audit.md).  
Schedule: `POST .../publication-package-jobs/{id}/schedule` (queued jobs, future `scheduled_for`).  
Due scan: `GET .../publishing-foundation/scheduled-jobs/due`.  
Dispatch: `POST .../publishing-foundation/scheduled-jobs/{id}/dispatch-due` (`dry_run` | `real`). No background loop.

## MVP E2E demo (AI.80–AI.85, frozen)

Audit: [phase_ai_85_mvp_demo_readiness_audit.md](phase_ai_85_mvp_demo_readiness_audit.md).  
Seed: `uv run python scripts/seed_e2e_demo.py`  
Status: `GET .../demo-flow/status` (development or `DEMO_FLOW_ENDPOINTS_ENABLED=true`).  
Provenance: `GET .../provenance/content-production/{publication_job_id}`.

## Beta readiness (AI.86–AI.90, frozen)

Audit: [phase_ai_90_beta_readiness_audit.md](phase_ai_90_beta_readiness_audit.md).  
Onboarding: `GET /me/onboarding`, `POST /me/onboarding/complete-step` (manual: `demo_seeded` only).  
Limits: `BETA_LIMITS_ENABLED` (429 `project_limit_exceeded`, etc.).  
Errors: JSON envelope with `error_code`, `safe_message`, `request_id`.  
Admin: `GET /me/beta-admin/dashboard` (development or `BETA_ADMIN_ENDPOINTS_ENABLED=true`).

## Beta QA loop (AI.91–AI.95, frozen)

Audit: [phase_ai_95_beta_qa_readiness_audit.md](phase_ai_95_beta_qa_readiness_audit.md).  
Feedback: `POST/GET /me/beta-feedback`, archive, sanitized `safe_context`.  
Admin: `GET /me/beta-admin/feedback`, triage/resolve, `GET /me/beta-admin/qa-export`.  
Demo markers: `failed_step`, `blocking_reason`, `last_error_code` on `demo-flow/status`.

## Beta launch pack (AI.96–AI.100, frozen)

Audit: [phase_ai_100_beta_launch_readiness_audit.md](phase_ai_100_beta_launch_readiness_audit.md).  
Access: `GET /me/beta-access`, admin approve/block; gate bypass in development.  
Guide: `GET /me/beta-guide`. Reset: `POST .../demo-flow/reset`. Smoke: `uv run python scripts/smoke_beta_launch.py`.

## Business campaign layer (AI.146–AI.155, frozen)

Audit: [phase_ai_155_campaign_layer_readiness_audit.md](phase_ai_155_campaign_layer_readiness_audit.md).  
BOS campaigns: `/projects/{id}/business-campaigns` (legacy Phase 9 stays at `/campaigns`).  
Regression: `uv run pytest tests/test_phase_ai_154_campaign_layer_regression.py -q`.

## Campaign control center (AI.156–AI.165, frozen)

Audit: [phase_ai_165_campaign_control_center_readiness_audit.md](phase_ai_165_campaign_control_center_readiness_audit.md).  
Status: `GET .../business-campaigns/{id}/control-center` — read-only health, next_action, timeline.  
List filters: `?view=control&health=&next_action_type=&failed_only=&completed_only=`.  
Regression: `uv run pytest tests/test_phase_ai_164_campaign_control_center_regression.py -q`.

## Campaign action center (AI.166–AI.175, frozen)

Audit: [phase_ai_175_campaign_action_center_readiness_audit.md](phase_ai_175_campaign_action_center_readiness_audit.md).  
Execute: `POST .../business-campaigns/{id}/actions/{action_type}/execute` (optional `Idempotency-Key`).  
Regression: `uv run pytest tests/test_phase_ai_174_campaign_action_center_regression.py -q`.

## General Business Operator (AI.176–AI.185, frozen)

Roadmap: [phase_ai_176_business_operator_roadmap.md](phase_ai_176_business_operator_roadmap.md).  
Audit: [phase_ai_185_business_operator_readiness_audit.md](phase_ai_185_business_operator_readiness_audit.md).  
Analyze: `POST .../business-operator/analyze` — rule-based intent, no LLM.  
Create: `POST .../business-operator/create-campaign` — campaign + scenario + control center; `metadata.source_business_intent`.  
Regression: `uv run pytest tests/test_phase_ai_184_business_operator_regression.py -q`.

## Business Operator assist mode (AI.186–AI.195, frozen)

Roadmap: [phase_ai_186_business_operator_assist_roadmap.md](phase_ai_186_business_operator_assist_roadmap.md).  
Audit: [phase_ai_195_business_operator_assist_readiness_audit.md](phase_ai_195_business_operator_assist_readiness_audit.md).  
Clarify: `POST .../business-operator/clarify` — merge answers into intent.  
Confidence gate: default threshold `0.65` (`BUSINESS_OPERATOR_CONFIDENCE_THRESHOLD`).  
Create blocked until gate passed (409). Preview/explanation without DB writes.  
Regression: `uv run pytest tests/test_phase_ai_194_business_operator_assist_regression.py -q`.

## Business Operator LLM fallback (AI.196–AI.205, frozen)

Roadmap: [phase_ai_196_business_operator_llm_fallback_roadmap.md](phase_ai_196_business_operator_llm_fallback_roadmap.md).  
Audit: [phase_ai_205_business_operator_llm_fallback_readiness_audit.md](phase_ai_205_business_operator_llm_fallback_readiness_audit.md).  
LLM runs only when rule confidence < threshold and `BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED=true` (default **false**).  
Merge: valid LLM output with higher confidence → `source=llm_fallback`; invalid → clarification.  
Regression: `uv run pytest tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q`.

## Campaign Brief Intake (AI.206–AI.215, frozen)

Roadmap: [phase_ai_206_campaign_brief_intake_roadmap.md](phase_ai_206_campaign_brief_intake_roadmap.md).  
Audit: [phase_ai_215_campaign_brief_intake_readiness_audit.md](phase_ai_215_campaign_brief_intake_readiness_audit.md).  
Analyze/clarify return in-memory `brief_draft` + `brief_completeness`.  
Complete: `POST .../business-operator/brief/complete` — merge answers, no DB.  
Confirm: `POST .../business-operator/brief/confirm` — persist confirmed brief.  
Create: `POST .../business-operator/create-campaign` — requires `{ intent, brief_id }`; gates: confidence + completeness.  
Provenance: `metadata.source_campaign_brief_id`; wizard plan `project_context.campaign_brief_summary`.  
Threshold: `CAMPAIGN_BRIEF_COMPLETENESS_THRESHOLD=100` (default).  
Regression: `uv run pytest tests/test_phase_ai_214_campaign_brief_intake_regression.py -q`.

## Marketing Data Tools v1 (AI.216–AI.225, frozen)

Roadmap: [phase_ai_216_marketing_data_tools_roadmap.md](phase_ai_216_marketing_data_tools_roadmap.md).  
Audit: [phase_ai_225_marketing_data_tools_readiness_audit.md](phase_ai_225_marketing_data_tools_readiness_audit.md).  
Tools: Wordstat (demand), Metrica (site), image generation (creative) — **mock only**, no external calls.  
Execute: `POST .../marketing-tools/{tool_type}/calls` — explicit only, no agent auto-call.  
Permissions: `MARKETING_DATA_TOOLS_ENABLED=false` (prod default); mock auto in dev via `MARKETING_DATA_TOOLS_MOCK_ENABLED=true`.  
Suggestions: `tool_suggestions` on Business Operator + Campaign Control Center (read-only).  
Regression: `uv run pytest tests/test_phase_ai_224_marketing_data_tools_regression.py -q`.

## Marketing Skills Layer v1 (AI.226–AI.235, frozen)

Roadmap: [phase_ai_226_marketing_skills_roadmap.md](phase_ai_226_marketing_skills_roadmap.md).  
Audit: [phase_ai_235_marketing_skills_readiness_audit.md](phase_ai_235_marketing_skills_readiness_audit.md).  
Skills: segment research, meaning unpacking, offer packaging/justification, wordstat/metrica analysis, visual report — **rule-based mock v1**.  
Run: `POST .../marketing-skills/{skill_type}/runs` — explicit only; data skills call tools only when `create_tool_call=true`.  
Suggestions: `skill_suggestions` on Campaign Control Center + UI skill panel.  
Permissions: `MARKETING_SKILLS_ENABLED=false` (prod default); mock auto in dev via `MARKETING_SKILLS_MOCK_ENABLED=true`.  
Regression: `uv run pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q`.

## Skill-Campaign Integration (AI.236–AI.245, frozen)

Roadmap: [phase_ai_236_skill_campaign_integration_roadmap.md](phase_ai_236_skill_campaign_integration_roadmap.md).  
Audit: [phase_ai_245_skill_campaign_integration_readiness_audit.md](phase_ai_245_skill_campaign_integration_readiness_audit.md).  
Flow: Brief → `CampaignSkillSuggestion` → explicit skill run (Action Center or skills panel) → `skill_context` on campaign → `campaign_skill_summaries` on plan.  
Actions: `run_segment_research`, `run_meaning_unpacking`, `run_offer_packaging`, `run_offer_justification`, `run_wordstat_research`, `run_metrica_analysis`, `run_visual_report` on Campaign Action Center.  
Regression: `uv run pytest tests/test_phase_ai_244_skill_campaign_integration_regression.py -q`.

## Campaign Supervisor Layer (AI.246–AI.255, frozen)

Roadmap: [phase_ai_246_campaign_supervisor_roadmap.md](phase_ai_246_campaign_supervisor_roadmap.md).  
Audit: [phase_ai_255_campaign_supervisor_readiness_audit.md](phase_ai_255_campaign_supervisor_readiness_audit.md).  
Report: `GET .../business-campaigns/{id}/supervisor-report` — read-only quality controller (no LLM, no tools, no side effects).  
Control Center: `supervisor_health_score`, finding counts, `top_findings` (max 5).  
Regression: `uv run pytest tests/test_phase_ai_254_campaign_supervisor_regression.py -q`.

## Campaign Workflow Layer (AI.256–AI.265, frozen)

Roadmap: [phase_ai_256_campaign_workflow_roadmap.md](phase_ai_256_campaign_workflow_roadmap.md).  
Audit: [phase_ai_265_campaign_workflow_layer_readiness_audit.md](phase_ai_265_campaign_workflow_layer_readiness_audit.md).  
Registry: `app/marketing/workflows/registry.py` — five reusable process templates (not Make-import).  
Inventory: `docs/WORKFLOW_RAW_INVENTORY.md`, `workflows/mapped/raw_inventory_index.json` (AI.257).  
Create run: `POST .../business-campaigns/{id}/workflows/{template_id}/create-run` — checklist only, no step execution.  
Control Center: `workflow_suggestions`, `active_workflow` (step checklist + linked actions + progress).  
Regression: `uv run pytest tests/test_phase_ai_264_campaign_workflow_layer_regression.py -q`.

## Knowledge Import Foundation (AI.255.1)

Map: [PROJECT_KNOWLEDGE_MAP.md](PROJECT_KNOWLEDGE_MAP.md).  
Import report: [KNOWLEDGE_IMPORT_REPORT.md](KNOWLEDGE_IMPORT_REPORT.md).  
Architecture: [KNOWLEDGE_ARCHITECTURE.md](KNOWLEDGE_ARCHITECTURE.md).  
Corpus roots: `knowledge/`, `skills/`, `workflows/raw/`, `standards/` — read-only until curated into product registries.  
Re-organize: `uv run python scripts/organize_knowledge_import.py`.

## Knowledge Governance (architecture + KG.2 ops)

Layered on H2.1–H2.5 SoT — lifecycle, KnowledgeObject, SemanticChunk, Benchmark, Citation Contract, freshness.

- **KG.1 (architecture):** contracts + policy helpers — no VectorDB / LLM retrieval.
- **KG.2 (operational):** PostgreSQL persistence → Operator API/UI → Published KnowledgeSnapshot → Runtime enforcement.

- ADR: [architecture/adr_knowledge_governance.md](architecture/adr_knowledge_governance.md)
- Volume: [architecture/knowledge_governance_volume.md](architecture/knowledge_governance_volume.md)
- RFC: [rfc_knowledge_governance.md](rfc_knowledge_governance.md)
- Developer Guide: [knowledge_governance_developer_guide.md](knowledge_governance_developer_guide.md)
- Manifest: [knowledge_governance_manifest.md](knowledge_governance_manifest.md)
- Runtime Invariants: [knowledge_governance_runtime_invariants.md](knowledge_governance_runtime_invariants.md)
- Overview: [knowledge_governance_subsystem.md](knowledge_governance_subsystem.md)
- Reuse/gap: [knowledge_governance_kg2_reuse_gap.md](knowledge_governance_kg2_reuse_gap.md)
- Ops package: `app/knowledge_governance/` · API: `/knowledge-governance/*` · migration `20260719_0050`
- Flag: `KNOWLEDGE_GOVERNANCE_RUNTIME_ENFORCED` (default true) — industrial domains require governed snapshot
- Invariants: `uv run pytest tests/test_architecture_knowledge_governance.py tests/test_phase_kg2_knowledge_governance_ops.py -q`

**Do not:** Pinecone, mass `/docs` index, Graph DB, auto-publish candidates, parallel Runtime.

## Marketsynth product roadmap (frontend ↔ backend)

**Completed:** Architecture V2.1 · Product Alpha A1–A6 · Product Alpha UX Freeze v1.0 · Integration **I1–I7** · Commercial MVP **P0.1–P0.6** · Commercial MVP **P1 Architecture Review** · Commercial MVP **P1.1** ImplementationPlan · Commercial MVP **P1.2** Controlled MarketingPlan Draft Handoff · Commercial MVP **P1.3** End-to-End Freeze ([commercial_mvp_p1_3_freeze_v1.md](commercial_mvp_p1_3_freeze_v1.md)) · **Commercial MVP Backend Baseline v1.0** · **CPH.1 Database and Migration Baseline** ([controlled_pilot_cph_1_database_baseline.md](controlled_pilot_cph_1_database_baseline.md)) · **CPH.2 Browser End-to-End** ([controlled_pilot_cph_2_browser_e2e.md](controlled_pilot_cph_2_browser_e2e.md)) · **CPH.3 Auth and Session Hardening** ([controlled_pilot_cph_3_auth_architecture.md](controlled_pilot_cph_3_auth_architecture.md)) · **CPH.4 Backup/Restore Operational Test** ([controlled_pilot_cph_4_backup_architecture.md](controlled_pilot_cph_4_backup_architecture.md)) · **CPH.5 Observability and Pilot Deployment** ([controlled_pilot_cph_5_deployment_architecture.md](controlled_pilot_cph_5_deployment_architecture.md)) · **Controlled Pilot Readiness Gate** → **CONDITIONAL_GO** ([controlled_pilot_readiness_gate.md](controlled_pilot_readiness_gate.md))  
**Current:** Pilot invite registration locally; resume Readiness Gate after owner activation  
**Next:** owner activates invite · then HTTPS cutover for remote 1–3 users · then V2.2 decision  
**Paused:** Product Alpha A7 · AI.592 · Architecture V2.2  

Principle: Commercial MVP Backend Baseline v1.0 frozen. Handoff creates MarketingPlan **draft only**; no automatic approval/execution.  
CPH.1: never `alembic stamp head` on orphan `20260608_0033`; use disposable PostgreSQL (`botfazer_cph1`) for pilot schema; SQLite `create_all` is not migration proof.  
CPH.2: Playwright browser E2E on `botfazer_cph1` + backend mode; orchestrator `scripts/cph2_run_browser_e2e.ps1`; UI prepare-handoff clears local gates before approve.  
CPH.3: browser HttpOnly cookie sessions + password login; API keys remain for non-browser clients; no permanent API key in localStorage; orchestrator `scripts/cph3_run_browser_e2e.ps1`.  
CPH.4: real `pg_dump`/`pg_restore` drill to `botfazer_cph4_restore_*`; checksum + lineage + session revoke (policy A); orchestrator `scripts/cph4_run_restore_drill.py`; backups outside git.  
CPH.5: OPTION B local reverse-proxy deploy; `/health/live` + `/health/ready`; pilot config fail-fast; correlation IDs; security headers; orchestrator `scripts/cph5_start_pilot.ps1`.
Pilot invites: one-time /activate-invite ([pilot_invite_registration.md](pilot_invite_registration.md)); operator scripts/create_pilot_invite.py; invite optional. Self-registration /register ([pilot_self_registration.md](pilot_self_registration.md)) when PUBLIC_SIGNUP_ENABLED; always member; production default off.
Password recovery: `/forgot-password` + `/reset-password`; `POST /auth/password-reset/*`; operator `scripts/create_password_reset_link.py` until email delivery is wired.
Home experience: `/workspace` conversational entry; agency dashboard at `/workspace/projects` ([home_experience_correction.md](home_experience_correction.md)).
Workspace IA: logo + domain section indexes ([workspace_information_architecture.md](workspace_information_architecture.md)); task projection ([workspace_task_projection.md](workspace_task_projection.md)).
UI i18n: ru/en dictionaries + Home layout v2 ([workspace_i18n_architecture.md](workspace_i18n_architecture.md)).
Phase H1 conversational intake: durable `UserRequest` + deterministic routing ([home_conversational_intake.md](home_conversational_intake.md)); Home visual freeze (Hero/USP) — do not redesign without explicit decision. Regression: `uv run pytest tests/test_phase_h1_user_request_routing.py tests/test_phase_h1_user_requests_api.py -q`.

## Phase H2.1–H2.2 — Knowledge Inventory & Specialist Skill Registry

Governed inventory + versioned skill contracts + capability packs — **no bulk `/docs` indexing, no embeddings, no AgentRun/LLM execution**.  
Docs: [knowledge_inventory.md](knowledge_inventory.md) · [knowledge_admission_policy.md](knowledge_admission_policy.md) · [knowledge_scope_and_tenancy.md](knowledge_scope_and_tenancy.md) · [skill_registry.md](skill_registry.md) · [specialist_capability_packs.md](specialist_capability_packs.md) · [skill_route_matrix.md](skill_route_matrix.md) · [knowledge_retrieval_policy.md](knowledge_retrieval_policy.md) · [knowledge_migration_manifest.md](knowledge_migration_manifest.md).  
Code: `app/knowledge_foundation/`, `app/specialist_skills/` (does **not** duplicate Agent Registry or marketing skill executors).  
API: `GET /knowledge-foundation/*`, `GET /specialist-skills/*` (draft-only diagnostics).  
UI: `/workspace/knowledge/manage`, `/workspace/settings/skills`.  
Regression: `uv run pytest tests/test_phase_h2_knowledge_skill_registry.py -q`.

## Phase H2.3–H2.5 — Approved ingestion + retrieval + UserRequest attachment

Durable `knowledge_items` / `knowledge_snapshots`; Pack A–D content foundation; deterministic retrieval; `content.telegram_post` reaches `ready_for_draft` **without** LLM/AgentRun.  
Docs: [knowledge_storage_model.md](knowledge_storage_model.md) · [approved_content_knowledge_pack.md](approved_content_knowledge_pack.md) · [knowledge_ingestion_manifest_v1.md](knowledge_ingestion_manifest_v1.md) · [knowledge_retrieval_adapter.md](knowledge_retrieval_adapter.md) · [knowledge_snapshot_policy.md](knowledge_snapshot_policy.md) · [user_request_skill_context.md](user_request_skill_context.md).  
Migration: `20260716_0042`.  
Regression: `uv run pytest tests/test_phase_h2_3_5_knowledge_attachment.py tests/test_phase_h2_knowledge_skill_registry.py tests/test_phase_h1_user_requests_api.py -q`.  

## Phase H2.6A — First executable skill: `design.image_generation`

Home image requests route to `image_generation` / `visual_specialist`. Feature flag `IMAGE_GENERATION_ENABLED` (default off). Provider: `IMAGE_GENERATION_PROVIDER=mock|openai_images`. Durable `generated_visual_assets` + conversation/Assets UI. No publication/campaigns/budgets.  
API: `GET /generated-visual-assets`, `GET /generated-visual-assets/{id}/content`, `GET /generated-visual-assets/readiness`.  
Migration: `20260716_0043`.  
Regression: `uv run pytest tests/test_phase_h2_6a_image_generation.py -q`.  

### H2.6A cutover — real provider + honest mock

- **Infrastructure gate:** passed (route → adapter → PNG → persist → preview → Assets).  
- **Product/visual gate:** requires `IMAGE_GENERATION_PROVIDER=openai_images` + valid backend `OPENAI_API_KEY`.  
- Mock results are **diagnostic only** (`generation_mode=mock`, badge «ТЕСТОВЫЙ РЕЖИМ») and never use “created from your description” copy.  
- Flags: `IMAGE_GENERATION_ENABLED`, `IMAGE_GENERATION_PROVIDER`, `ALLOW_MOCK_IMAGE_RESULTS`.  
- Migration: `20260716_0044` (`generation_mode`, `asset_type`).  
- Do **not** start H2.6B until owner visually accepts a real image.

### H2.6A-R — Reference images & identity preservation (before H2.6B)

- Upload up to **15** owner-scoped reference images per Reference Set; provider receives a **ranked subset** (`REFERENCE_PROVIDER_MAX_IMAGES`, default 10).  
- Limits are **server-enforced** (`REFERENCE_IMAGE_*` in config / `.env`).  
- MIME: PNG/JPEG/WebP; EXIF stripped; checksum de-dupe; authenticated content only.  
- Honest copy only: maximize identity/brand consistency + mandatory owner review — **never** claim guaranteed 100% preservation.  
- Exact logos prefer deterministic compositing over generative redraw.  
- Docs: [reference_image_domain.md](reference_image_domain.md) · [reference_set_policy.md](reference_set_policy.md) · [identity_preservation_policy.md](identity_preservation_policy.md) · [brand_asset_preservation.md](brand_asset_preservation.md) · [reference_upload_security.md](reference_upload_security.md) · [image_provider_reference_selection.md](image_provider_reference_selection.md) · [generative_vs_deterministic_visuals.md](generative_vs_deterministic_visuals.md).  
- Migration: `20260716_0045`.  
- Regression: `uv run pytest tests/test_phase_h2_6a_r_reference_images.py -q`.  
- Product gate still blocked until a valid real OpenAI image result is accepted by owner.

## Phase H2.7 — Specialist Execution Foundation (slice 1)

Governed draft-only path for the first text skill `content.telegram_post`:

`UserRequest → skill → Knowledge Snapshot → PromptPackage → Tool Profile → LLM → Quality Gate → owner review`.

- Feature flag: `CONTENT_DRAFT_EXECUTION_ENABLED` (default off). Provider/model: `CONTENT_DRAFT_LLM_PROVIDER` / `CONTENT_DRAFT_LLM_MODEL` (`mock` | `openai` | `openrouter`).
- Integration Registry (`app/integrations/`), BusinessTools (`app/business_tools/`), Tool Profiles (`app/specialist_skills/tool_profiles.py`).
- Prompt assembler (`app/prompts/specialist/`). Constitutional + role + skill instruction packages.
- OpenRouter added as an LLM adapter option (no direct skill access to keys).
- Firecrawl / XMLRiver: read-only adapters only (Source candidates, no Evidence).
- n8n: **blocked**. Make / Pinecone / Yandex Direct writes: disabled behind approval boundaries.
- UI: Specialist Activity card with «Экспертиза» + review actions (no publish).
- Migration: `20260716_0046`.
- Docs: [h2_7_execution_foundation.md](h2_7_execution_foundation.md) · [integration_registry.md](integration_registry.md) · [business_tool_abstraction.md](business_tool_abstraction.md) · [tool_profiles.md](tool_profiles.md) · [prompt_package_architecture.md](prompt_package_architecture.md) · [prompt_assembly_policy.md](prompt_assembly_policy.md) · [specialist_role_prompts.md](specialist_role_prompts.md) · [specialist_expertise_ui.md](specialist_expertise_ui.md) · [external_execution_boundaries.md](external_execution_boundaries.md).
- Regression: `uv run pytest tests/test_phase_h2_7_specialist_execution.py -q`.
- Owner acceptance fix: CTA semantic extraction («В конце задай вопрос»), Telegram length default `standard`, natural user copy (no route/skill/snapshot jargon). Real draft requires `CONTENT_DRAFT_EXECUTION_ENABLED=true` + text model + `uv sync --extra llm`.

## Phase H2.8 — Content Expertise & Editorial Quality

Editorial pipeline inside `content.telegram_post`: domain classification, drilling domain pack, claim verification, editorial review, strict quality gate (max one revision). No new product skills, no publication.

- Docs: [h2_8_content_expertise.md](h2_8_content_expertise.md)
- Regression: `uv run pytest tests/test_phase_h2_8_content_expertise.py -q`

## Phase H2.8A — Owner Product Acceptance (Content UI + Image Fidelity)

Closes browser content gate and roses prompt/reference fidelity defect.

- Docs: [h2_8a_owner_acceptance.md](h2_8a_owner_acceptance.md)
- Regression: `uv run pytest tests/test_phase_h2_8a_owner_acceptance.py -q`

## Phase H2.8B — Reference Fidelity

Reference sets, identity profile, awaiting_identity_review, strengthen likeness.

- Docs: [h2_8b_reference_fidelity.md](h2_8b_reference_fidelity.md)
- Regression: `uv run pytest tests/test_phase_h2_8b_reference_fidelity.py -q`

## Phase H2.8C — Reference Composer UX

Composer UX for preserve traits / generate / review. Does **not** accept Identity Product Gate.

- Docs: [h2_8c_reference_composer.md](h2_8c_reference_composer.md)
- Regression: `uv run pytest tests/test_phase_h2_8c_reference_composer.py -q`

## Phase H2.8D — Identity Engine Audit & Provider Decision

Freeze failed baseline, honest transmit lineage, identity/style selection (max 5), `person_identity_preservation` + `IdentityImageProvider`, quality gate, gated A/B harness. Identity Product Gate remains **NOT owner-accepted**.

- Docs: [h2_8d_identity_engine.md](h2_8d_identity_engine.md)
- Regression: `uv run pytest tests/test_phase_h2_8d_identity_engine.py tests/test_phase_h2_8b_reference_fidelity.py tests/test_phase_h2_8c_reference_composer.py -q`
- Flags: `REFERENCE_IDENTITY_MAX_IMAGES=5`, `IDENTITY_AB_HARNESS_ENABLED=false` (paid calls also need `owner_confirmed_paid_calls`)

## Phase H2.8E — Identity Generation Subsystem & Provider Qualification

Governed subsystem over existing `design.image_generation`: provider registry, immutable manifest SoT, preflight, paid approval, qualification operator, Home readiness wiring, runbook. **No new product skill.** Gate still **NOT accepted**; no auto four paid calls.

- **Slice 0 (required first):** [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md) · [architecture/adr_subsystem_standard.md](architecture/adr_subsystem_standard.md) · [architecture/subsystem_compliance_matrix.md](architecture/subsystem_compliance_matrix.md)
- Docs: [h2_8e_identity_subsystem.md](h2_8e_identity_subsystem.md) · [identity_generation_operator_runbook.md](identity_generation_operator_runbook.md) · [identity_provider_capability_matrix.md](identity_provider_capability_matrix.md)
- Regression: `uv run pytest tests/test_phase_h2_8e_identity_subsystem.py tests/test_phase_h2_8d_identity_engine.py tests/test_architecture_subsystem_standard.py -q`
- Migration: `20260719_0049`

**Next slice:** owner diagnostic approval → capability decision; if unsuitable → H2.9 specialized identity provider (not prompt tuning). Do not enable Make/n8n/publication from this track. Do not run paid calls without explicit owner confirmation.

**Next slice (legacy):** `programmer.telegram_bot_spec` (still draft-only). Do not enable Make/n8n execution or research skills without a new approved slice. Do not start Campaign / publication until Identity Gate is owner-accepted.

## Forbidden in foundation phase

- LangGraph graphs (marketing pipeline — unless phase explicitly requests)
- Direct OpenAI/Anthropic SDK calls (use LiteLLM later)
- Copy-paste from old `serve.js` without mapping to contracts
- Parallel frontend Runtime / Control Center / MarketingPlan engines

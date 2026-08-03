# Marketsynth — instructions for AI assistants

You are working on **Marketsynth** (Python 3.12, FastAPI).  
Legacy working name / package label: **BotFazer** — do not globally rename internals without an explicit migration phase.

## Source of Truth (read first on cold start)

AI development working memory — not user docs:

1. [knowledge/00_INDEX.md](knowledge/00_INDEX.md) — status, links, update rules
2. [knowledge/06_CURRENT_STATE.md](knowledge/06_CURRENT_STATE.md) — reality now; **read `## Active Execution` first**
3. [knowledge/15_SESSION_LOG.md](knowledge/15_SESSION_LOG.md) — last session handoff

Scalable archives: `knowledge/decisions/`, `sessions/`, `milestones/`, `audits/`, `research/`.  
After significant work: update Current State, Changelog, Session Log (see `knowledge/00_INDEX.md`).

## Cold Start Protocol

**Do not modify code before completing steps 1–4.**

1. **Read SoT** — `knowledge/00_INDEX.md` → `knowledge/06_CURRENT_STATE.md` (`## Active Execution`) → `knowledge/15_SESSION_LOG.md`
2. **Restore context** — active program, milestone, task, blockers, and what is frozen
3. **Verify consistency** — if SoT conflicts with `docs/product/PRODUCT-FINISH-01*` or owner rejection record, report the conflict; do not assume or invent state
4. **Report current execution point** — Program, milestone, current task, Definition of Done, next task (from `## Active Execution`)
5. **Wait for owner instructions** — do not start implementation until owner confirms or explicitly requests the current task

After owner acceptance of a task: update `06_CURRENT_STATE.md`, `14_CHANGELOG.md`, `15_SESSION_LOG.md` before moving to the next task.

## Cursor Development Governance (internal)

Process for Cursor agent work — **not** a product program. See [docs/cursor/CURSOR-GOVERNANCE.md](docs/cursor/CURSOR-GOVERNANCE.md).

- **Planning Gate:** `.cursor/rules/marketsynth-planning-gate.mdc` — before product code edits
- **Composite review:** `.cursor/skills/marketsynth-composite-review/SKILL.md` — after non-trivial changes
- **Delivery report:** `.cursor/rules/marketsynth-delivery-report.mdc` — brief PASS/FAIL with evidence

Active product priority remains in `knowledge/06_CURRENT_STATE.md` (`## Active Execution`).

## Strategic project context

Read these before architectural or product decisions:

- [docs/architecture/marketsynth_subsystem_standard.md](docs/architecture/marketsynth_subsystem_standard.md) — **canonical Subsystem Standard** (lifecycle, operator, manifest, recipes, honest capability)
- [docs/architecture/adr_subsystem_standard.md](docs/architecture/adr_subsystem_standard.md) — ADR: governed subsystems for substantial capabilities
- [docs/architecture/adr_knowledge_governance.md](docs/architecture/adr_knowledge_governance.md) — ADR: Knowledge Governance Architecture
- [docs/architecture/subsystem_compliance_matrix.md](docs/architecture/subsystem_compliance_matrix.md) — compliance gaps (audit only)
- [docs/knowledge_governance_subsystem.md](docs/knowledge_governance_subsystem.md) — Knowledge Governance (KG.1 architecture + KG.2 ops; no VectorDB)
- [docs/knowledge_governance_kg2_reuse_gap.md](docs/knowledge_governance_kg2_reuse_gap.md) — KG.2 reuse/gap matrix
- [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md) — **why** · AI Business OS
- [docs/product/MARKETSYNTH-PLATFORM-MAP.md](docs/product/MARKETSYNTH-PLATFORM-MAP.md) — **what** · canonical product inventory (12 domains + pillars)
- [docs/MARKETSYNTH-OPERATING-MODEL.md](docs/MARKETSYNTH-OPERATING-MODEL.md) — **how** · runtime loop, lifecycle, shared services, module invariant (**read before new modules**)
- [docs/AGENT_OS_ARCHITECTURE.md](docs/AGENT_OS_ARCHITECTURE.md) — Agent = Instructions + Knowledge + Skills + Tools + Memory + Workflows + Commands + Supervisor
- [docs/MARKETING_AGENT_TARGET_MODEL.md](docs/MARKETING_AGENT_TARGET_MODEL.md) — business-first outputs, Wordstat/Metrica/image when justified
- [docs/MARKETING_FRAMEWORKS_CONTEXT.md](docs/MARKETING_FRAMEWORKS_CONTEXT.md) — segment, meaning, offer packaging, justification frameworks
- [docs/KNOWLEDGE_IMPORT_PLAN.md](docs/KNOWLEDGE_IMPORT_PLAN.md) — staging → corpus → curated product mapping
- [docs/CURSOR_OPERATING_RULES.md](docs/CURSOR_OPERATING_RULES.md) — gates, frozen layers, safe summaries, no auto-run
- [docs/PRODUCT_CONSTITUTION.md](docs/PRODUCT_CONSTITUTION.md) — **master Product Constitution index**
- [docs/HOME_PRODUCT_RULE.md](docs/HOME_PRODUCT_RULE.md) — **Product Constitution Ch.1**: commercial rules; Home = business decisions, not AI control panel
- [docs/VIDEO_STUDIO_PRODUCT.md](docs/VIDEO_STUDIO_PRODUCT.md) — **Product Constitution Ch.2**: Video Studio (ACCEPTED WITH PATCHES); AI Director, Scene Graph, Video Router

**Rule:** New domains, skills, integrations, and execution paths must be evaluated against the **[Operating Model](docs/MARKETSYNTH-OPERATING-MODEL.md)** (§8 plug-in checklist) and the **Marketsynth Subsystem Standard** before implementation. A working service/API alone is not a complete subsystem. Do not add a second Runtime or Agent Registry. Knowledge-backed agent answers must honor the Citation Contract (Answer + Evidence + Source + Confidence). For industrial domains (`drilling_operations` / `industrial_safety` / `oil_and_gas`), specialist attachment uses only published+fresh governed KnowledgeSnapshots; otherwise `insufficient_governed_knowledge` blocks execution.

## Owner product track (commercial constitution + video)

- **Product Constitution:** [PRODUCT_CONSTITUTION.md](docs/PRODUCT_CONSTITUTION.md) · Ch.1 [HOME_PRODUCT_RULE.md](docs/HOME_PRODUCT_RULE.md) · Ch.2 [VIDEO_STUDIO_PRODUCT.md](docs/VIDEO_STUDIO_PRODUCT.md) (Director ≠ Premiere, Scene Graph, Video Router).
- **VS.1 Foundation** implemented — paid smoke via `POST /media-generation/video-smoke/execute` + `explicit_confirmation=true` flips readiness.
- **VS.2A-P-R accepted (2026-07-22):** image→video persistence in Commercial Home (`691dccc`). Owner preview at `?owner_preview=video`.
- **VIDEO = FROZEN** until Controlled Pilot completes — no VS.2B, text-to-video, start/end frame, long-form, montage, identity video, or new video providers. P0 bugfixes on accepted i2v path only.
- **Project Freeze baseline:** tag `project-freeze-2026-07-22` — residual WIP stashed.
- **CMVP.1 / CMVP.1.1 accepted** — Business Idea Validator (evidence-backed research, gap-directed coverage, backend hydration). Commits through `006b087`.
- **KB-WPL-01 closed (2026-07-24):** integrated freeze audit accepted — program hash `43e2cab3…`. **Do not start KB-WPL-02** until Product Track P0 slice is owner-accepted.
- **Active track: Product (PRODUCT-01.3)** — BIV intake, evidence and report integrity repair (**P0**, blocks re-acceptance). PRODUCT-01.2 **rejected_with_findings** (2026-07-24). Offer Builder runtime exists but **not frozen**. Parallel: **CONN-HF-01.1L** (owner token gates). After PRODUCT-01.3 + re-acceptance + PRODUCT-00.5: **PRODUCT-MEDIA-01**.
- **CWF.1 / CWF.1a** — Commercial Workflow: Idea → Verdict → Launch Pack → Telegram. See `.cursor/rules/commercial-product-directive.mdc` and [CWF-SKILL-INTEGRATION-GAPS.md](docs/product/CWF-SKILL-INTEGRATION-GAPS.md). **Commercial UI gate (order):** [COMMERCIAL_USER_JOURNEY_MAP.md](docs/COMMERCIAL_USER_JOURNEY_MAP.md) → [INFORMATION_ARCHITECTURE.md](docs/INFORMATION_ARCHITECTURE.md) → [DESIGN.md](docs/DESIGN.md) → implementation.
- **Research track: SKILL-R0** — Skill/MCP audit foundation only (`docs/research/`). No runtime, no new MCP, no CWF.1 changes until RFC acceptance + owner gate.
- **Willingness-to-pay gate:** every PR must increase customer value / repeat payment readiness — not feature count.

## Owner product track (H2.8x — visual identity)

- **Architecture Patch Digital Identity v1.0:** **ACCEPTED WITH UI DECOUPLING CONDITION**. DIS implementation **FORBIDDEN** until after CGP.10C acceptance + narrow vertical slices.
- **Active UI sprint:** [docs/phase_cgp_10c_deliverable_selection_ux.md](docs/phase_cgp_10c_deliverable_selection_ux.md) — deliverable-aware Home (no ambiguous «Продолжить»).
- Architecture pack: [docs/architecture_patch_digital_identity_v1.md](docs/architecture_patch_digital_identity_v1.md) · [docs/rfc_digital_identity_system_v2.md](docs/rfc_digital_identity_system_v2.md) · [docs/rfc_patch_matrix.md](docs/rfc_patch_matrix.md) · [docs/identity_architecture_decision_log.md](docs/identity_architecture_decision_log.md).
- Thesis: Marketsynth manages typed business identity assets; Home must choose **what to create** before identity/DIS work resumes.
- **H2.8E Slice 0 (standard):** [docs/architecture/marketsynth_subsystem_standard.md](docs/architecture/marketsynth_subsystem_standard.md) — project-wide subsystem lifecycle; Identity maps to it.
- **H2.8E (current):** Identity Generation Subsystem — registry, immutable manifest, preflight, paid approval, qualification operator, Home readiness. Docs: [docs/h2_8e_identity_subsystem.md](docs/h2_8e_identity_subsystem.md) · [docs/identity_generation_operator_runbook.md](docs/identity_generation_operator_runbook.md). Regression: `uv run pytest tests/test_phase_h2_8e_identity_subsystem.py tests/test_phase_h2_8d_identity_engine.py tests/test_architecture_subsystem_standard.py -q`.
- **H2.8D:** honest provider transmit lineage, max 5 identity refs, `person_identity_preservation`. Docs: [docs/h2_8d_identity_engine.md](docs/h2_8d_identity_engine.md).
- Identity Product Gate is **NOT ACCEPTED** until the owner recognizes the person after a real diagnostic. Do not start Campaign / Make / n8n / publication from this track. Do **not** run paid A/B without explicit owner approval. If provider unsuitable → specialized engine / LoRA contour, not prompt-tuning alone.

## Current phase: marketing production conveyor (AI.27–AI.33 done)

- **Done:** plan persistence, execution runs, specialist output artifacts, Strategist / Researcher / Content Planner dry-run execution.
- **Marketing department v2 (AI.110–AI.125, frozen at AI.119):** baseline **14 roles** (frozen six + eight v2 executables). Roadmap: [docs/phase_ai_110_marketing_department_v2_roadmap.md](docs/phase_ai_110_marketing_department_v2_roadmap.md). Freeze: [docs/phase_ai_119_marketing_department_v2_freeze.md](docs/phase_ai_119_marketing_department_v2_freeze.md). Readiness: [docs/phase_ai_125_marketing_department_v2_readiness_audit.md](docs/phase_ai_125_marketing_department_v2_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q`. Optional v2 demo seed: `uv run python scripts/seed_e2e_demo.py --include-v2-marketing`.
- **Product Scenario Builder (AI.126–AI.135):** five business scenarios over the 14-role department — registry in `app/marketing/scenarios/`, `POST .../marketing-scenarios/{id}/create-plan` (draft plan only). Roadmap: [docs/phase_ai_126_scenario_roadmap.md](docs/phase_ai_126_scenario_roadmap.md). Readiness: [docs/phase_ai_135_scenario_builder_readiness_audit.md](docs/phase_ai_135_scenario_builder_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_134_scenario_builder_regression.py -q`. Optional scenario seed: `uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen`.
- **Scenario Auto-Run Wizard (AI.136–AI.145):** manual step wizard over existing APIs — `POST .../scenario-wizard-runs/{id}/advance` (one step only). Roadmap: [docs/phase_ai_136_scenario_wizard_roadmap.md](docs/phase_ai_136_scenario_wizard_roadmap.md). Readiness: [docs/phase_ai_145_scenario_wizard_readiness_audit.md](docs/phase_ai_145_scenario_wizard_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_144_scenario_wizard_regression.py -q`. Optional seed: `uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen`.
- **Business Campaign Layer (AI.146–AI.155):** BOS `Campaign` container at `/projects/{id}/business-campaigns` (not legacy `/campaigns`). Roadmap: [docs/phase_ai_146_campaign_layer_roadmap.md](docs/phase_ai_146_campaign_layer_roadmap.md). Readiness: [docs/phase_ai_155_campaign_layer_readiness_audit.md](docs/phase_ai_155_campaign_layer_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_154_campaign_layer_regression.py -q`.
- **Campaign Control Center (AI.156–AI.165):** read-only command panel — `GET .../business-campaigns/{id}/control-center` (health, next_action, timeline). Roadmap: [docs/phase_ai_156_campaign_control_center_roadmap.md](docs/phase_ai_156_campaign_control_center_roadmap.md). Readiness: [docs/phase_ai_165_campaign_control_center_readiness_audit.md](docs/phase_ai_165_campaign_control_center_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_164_campaign_control_center_regression.py -q`.
- **Campaign Action Center (AI.166–AI.175):** explicit action buttons — `POST .../business-campaigns/{id}/actions/{action_type}/execute`. Roadmap: [docs/phase_ai_166_campaign_action_center_roadmap.md](docs/phase_ai_166_campaign_action_center_roadmap.md). Readiness: [docs/phase_ai_175_campaign_action_center_readiness_audit.md](docs/phase_ai_175_campaign_action_center_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_174_campaign_action_center_regression.py -q`.
- **General Business Operator (AI.176–AI.185):** rule-based intent → scenario → campaign. Roadmap: [docs/phase_ai_176_business_operator_roadmap.md](docs/phase_ai_176_business_operator_roadmap.md). Readiness: [docs/phase_ai_185_business_operator_readiness_audit.md](docs/phase_ai_185_business_operator_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_184_business_operator_regression.py -q`.
- **Business Operator Assist Mode (AI.186–AI.195):** clarifications, confidence gate (0.65), explanation, preview, explicit confirm — no LLM. Roadmap: [docs/phase_ai_186_business_operator_assist_roadmap.md](docs/phase_ai_186_business_operator_assist_roadmap.md). Readiness: [docs/phase_ai_195_business_operator_assist_readiness_audit.md](docs/phase_ai_195_business_operator_assist_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_194_business_operator_assist_regression.py -q`.
- **Business Operator LLM Fallback (AI.196–AI.205):** optional LLM when rule confidence low — off by default, no auto-create. Roadmap: [docs/phase_ai_196_business_operator_llm_fallback_roadmap.md](docs/phase_ai_196_business_operator_llm_fallback_roadmap.md). Readiness: [docs/phase_ai_205_business_operator_llm_fallback_readiness_audit.md](docs/phase_ai_205_business_operator_llm_fallback_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q`.
- **Campaign Brief Intake (AI.206–AI.215):** brief draft + completeness gate before campaign create — confirmed `brief_id` required. Roadmap: [docs/phase_ai_206_campaign_brief_intake_roadmap.md](docs/phase_ai_206_campaign_brief_intake_roadmap.md). Readiness: [docs/phase_ai_215_campaign_brief_intake_readiness_audit.md](docs/phase_ai_215_campaign_brief_intake_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_214_campaign_brief_intake_regression.py -q`.
- **Marketing Data Tools v1 (AI.216–AI.225):** Wordstat / Metrica / image generation mock tools — explicit API calls only. Roadmap: [docs/phase_ai_216_marketing_data_tools_roadmap.md](docs/phase_ai_216_marketing_data_tools_roadmap.md). Readiness: [docs/phase_ai_225_marketing_data_tools_readiness_audit.md](docs/phase_ai_225_marketing_data_tools_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_224_marketing_data_tools_regression.py -q`.
- **Marketing Skills Layer v1 (AI.226–AI.235):** professional skill processes over tools — explicit runs only. Roadmap: [docs/phase_ai_226_marketing_skills_roadmap.md](docs/phase_ai_226_marketing_skills_roadmap.md). Readiness: [docs/phase_ai_235_marketing_skills_readiness_audit.md](docs/phase_ai_235_marketing_skills_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q`.
- **Skill-Campaign Integration (AI.236–AI.245):** skills as campaign brain — suggestions, context merge, action center runs. Roadmap: [docs/phase_ai_236_skill_campaign_integration_roadmap.md](docs/phase_ai_236_skill_campaign_integration_roadmap.md). Readiness: [docs/phase_ai_245_skill_campaign_integration_readiness_audit.md](docs/phase_ai_245_skill_campaign_integration_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_244_skill_campaign_integration_regression.py -q`.
- **Campaign Supervisor Layer (AI.246–AI.255):** read-only quality controller for gaps, contradictions, risks. Roadmap: [docs/phase_ai_246_campaign_supervisor_roadmap.md](docs/phase_ai_246_campaign_supervisor_roadmap.md). Readiness: [docs/phase_ai_255_campaign_supervisor_readiness_audit.md](docs/phase_ai_255_campaign_supervisor_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_254_campaign_supervisor_regression.py -q`.
- **Campaign Workflow Layer (AI.256–AI.265):** reusable process templates inside campaigns — registry + recommendations + checklist runs (no auto-execution). Roadmap: [docs/phase_ai_256_campaign_workflow_roadmap.md](docs/phase_ai_256_campaign_workflow_roadmap.md). Readiness: [docs/phase_ai_265_campaign_workflow_layer_readiness_audit.md](docs/phase_ai_265_campaign_workflow_layer_readiness_audit.md). Regression: `uv run pytest tests/test_phase_ai_264_campaign_workflow_layer_regression.py -q`.
- **Knowledge Import Foundation (AI.255.1):** imported corpus in repo — `knowledge/`, `skills/`, `workflows/raw/`, `standards/`. Map: [docs/PROJECT_KNOWLEDGE_MAP.md](docs/PROJECT_KNOWLEDGE_MAP.md). Report: [docs/KNOWLEDGE_IMPORT_REPORT.md](docs/KNOWLEDGE_IMPORT_REPORT.md). Architecture: [docs/KNOWLEDGE_ARCHITECTURE.md](docs/KNOWLEDGE_ARCHITECTURE.md).
- **Workflow Library Pilot + `automation.n8n_workflow`:** first 50 sanitized n8n templates (variant B — not full 1023). Draft JSON + download only; no import/execution. Owner review: [docs/workflow_library_pilot_owner_review.md](docs/workflow_library_pilot_owner_review.md). Regression: `uv run pytest tests/test_workflow_library_pilot.py -q`. Video generation remains BLOCKED until image-to-video provider is chosen.
- **Marketing pipeline (frozen AI.27–AI.39):** [docs/phase_ai_39_marketing_pipeline_readiness_audit.md](docs/phase_ai_39_marketing_pipeline_readiness_audit.md).
- **Content production (AI.40–AI.45, frozen):** [docs/phase_ai_45_content_production_readiness_audit.md](docs/phase_ai_45_content_production_readiness_audit.md)
- **Media production (AI.50–AI.55, frozen):** [docs/phase_ai_55_media_production_readiness_audit.md](docs/phase_ai_55_media_production_readiness_audit.md)
- **Media generation (AI.56–AI.59, frozen):** [docs/phase_ai_59_media_generation_readiness_audit.md](docs/phase_ai_59_media_generation_readiness_audit.md)
- **Publishing foundation (AI.60–AI.65, frozen):** [docs/phase_ai_65_publishing_foundation_readiness_audit.md](docs/phase_ai_65_publishing_foundation_readiness_audit.md)
- **Publishing reliability (AI.66–AI.69, frozen):** [docs/phase_ai_69_publishing_reliability_readiness_audit.md](docs/phase_ai_69_publishing_reliability_readiness_audit.md)
- **Telegram publishing (AI.70–AI.75, frozen):** [docs/phase_ai_75_telegram_publishing_readiness_audit.md](docs/phase_ai_75_telegram_publishing_readiness_audit.md) — gated real send; **no Instagram/LinkedIn**.
- **Publishing scheduler (AI.76–AI.79, frozen):** [docs/phase_ai_79_publishing_scheduler_readiness_audit.md](docs/phase_ai_79_publishing_scheduler_readiness_audit.md) — schedule approved package jobs only; explicit due scan + dispatch; **no background worker**.
- **MVP E2E demo (AI.80–AI.85, frozen):** [docs/phase_ai_85_mvp_demo_readiness_audit.md](docs/phase_ai_85_mvp_demo_readiness_audit.md) — `scripts/seed_e2e_demo.py`, demo-flow status, provenance, UI checklist.
- **Beta readiness (AI.86–AI.90, frozen):** [docs/phase_ai_90_beta_readiness_audit.md](docs/phase_ai_90_beta_readiness_audit.md) — onboarding, soft limits, API error envelope, beta admin dashboard.
- **Beta QA loop (AI.91–AI.95, frozen):** [docs/phase_ai_95_beta_qa_readiness_audit.md](docs/phase_ai_95_beta_qa_readiness_audit.md) — feedback reports, admin triage, demo failure markers, safe QA export.
- **Beta launch pack (AI.96–AI.100, frozen):** [docs/phase_ai_100_beta_launch_readiness_audit.md](docs/phase_ai_100_beta_launch_readiness_audit.md) — access gate, tester guide, demo reset, smoke script.
- Implement **one phase per PR**; contracts in `app/schemas/contracts.py` first; reuse `POST .../execute-specialist`.
- H2.9A / KG.3 `research.web_source_collection` is bounded, read-only Source Candidate collection; explicit admission creates only a draft Knowledge candidate. No Evidence, verdict, Campaign, Make/n8n, or publication.
- **Do not** add LangGraph marketing orchestration, parallel specialist execution, auto `ContentAsset`, web/MCP research, or Media tooling unless the active phase explicitly allows it.

## Mandatory rules

1. Read `docs/DEVELOPMENT.md` and `app/schemas/contracts.py` before new features.
2. All settings via `app/core/config.py` — never hardcode API keys.
3. Sanitize inbound user content with `app/core/security.py`.
4. New entities → add to `contracts.py` first, then DB, then API.
5. Every endpoint needs tests under `tests/`.
6. After each UX / product-UI sprint: run the product and get **owner visual acceptance** before the next sprint (see `.cursor/rules/owner-visual-acceptance.mdc`, `docs/CURSOR_OPERATING_RULES.md` §11).
## Commands

```bash
cd botfazer
uv sync --extra dev
cp .env.example .env
uv run uvicorn app.main:app --reload
uv run pytest
```

# API Overview

> **Contract SoT:** [app/schemas/contracts.py](../app/schemas/contracts.py)  
> **Handlers:** `app/api/` — thin HTTP only  
> **Last updated:** 2026-07-29

---

## Conventions

| Rule | Detail |
|------|--------|
| Base | FastAPI, Python 3.12 |
| Auth | Session/API key via `app/api/dependencies/auth.py` |
| Errors | Beta envelope (AI.86–90) |
| Sanitization | All inbound text through security layer |
| Versioning | No formal `/v1` prefix today — contract-first in Pydantic |
| Tests | Every new endpoint → `tests/` |

**Run locally:**
```bash
uv run uvicorn app.main:app --reload
```

---

## Route groups (by domain)

### Core & workspace

| Prefix / route file | Purpose |
|---------------------|---------|
| `projects.py` | Project CRUD |
| `routes/auth.py`, `me.py`, `users.py` | Auth, profile |
| `routes/user_requests.py` | User request queue |
| `routes/chat.py`, `agent_chat.py` | Chat interfaces |
| `health.py` | Health check |

### Commercial / CWF

| Route file | Purpose |
|------------|---------|
| `routes/business_idea_validation.py` | BIV runtime |
| `routes/commercial_research.py` | Commercial research |
| `routes/evidence.py` | Evidence artifacts |
| `routes/business_verdicts.py` | Verdict persistence |
| `routes/launch_pack.py` | Launch Pack requests |
| `routes/offers.py` | Offer Builder |
| `routes/analysis_contexts.py` | Analysis context |
| `routes/marketing_strategies.py` | Strategy artifacts |
| `routes/content_factory.py` | Content Factory |

### Marketing conveyor

| Route file | Purpose |
|------------|---------|
| `routes/marketing_plans.py` | Plan persistence |
| `routes/marketing_plan_execution_runs.py` | Execution runs |
| `routes/marketing_specialist_outputs.py` | Specialist artifacts |
| `routes/marketing_scenarios.py` | Scenario plans |
| `routes/scenario_wizard_runs.py` | Wizard steps |
| `routes/business_campaigns.py` | Campaign layer |
| `routes/business_operator.py` | Intent → campaign |
| `routes/marketing_skills.py` | Skill runs |
| `routes/marketing_tools.py` | Tool invocations |
| `routes/marketing_briefs.py`, `project_briefs.py` | Brief intake |
| `routes/marketing_campaigns.py`, `marketing_funnels.py` | Legacy/frozen paths |

### Media & video

| Route file | Purpose |
|------------|---------|
| `routes/media_briefs.py` | Media briefs |
| `routes/media_generation.py` | Generation jobs |
| `routes/media_assets.py` | Asset storage |
| `routes/generated_visual_assets.py` | Visual assets |
| `routes/reference_visuals.py` | Reference sets |
| `routes/video_studio.py` | Video studio |
| `routes/video_clips.py` | Clip requests |
| `routes/video_smoke_preview.py` | Smoke preview |
| `routes/video_smoke_execute.py` | Paid smoke execute |
| `routes/media_renderer.py`, `signed_media.py` | Media delivery |

### Publishing

| Route file | Purpose |
|------------|---------|
| `routes/publishing_foundation.py` | Channel foundation |
| `routes/publication_packages.py` | Packages |
| `routes/publishing.py` | Publication jobs |
| `routes/content_assets.py` | Content assets |

### Identity & knowledge

| Route file | Purpose |
|------------|---------|
| `routes/identity_generation.py` | H2.8E subsystem |
| `routes/knowledge_governance.py` | KG ops |
| `routes/knowledge_foundation.py` | Knowledge foundation |
| `routes/specialist_skills.py` | Specialist skill bridge |
| `routes/sources.py` | Source candidates |
| `routes/investigations.py` | Investigations (legacy) |

### Demo & beta

| Route file | Purpose |
|------------|---------|
| `routes/demo_flow.py` | Demo flow status |
| `routes/agents.py`, `agent_runs.py` | Agent runs |
| `routes/llm_requests.py` | LLM request log |
| `routes/implementation_plans.py` | Implementation plans |

---

## Key endpoints (commercial golden path)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/projects/{id}/business-idea-validation/...` | BIV analysis |
| GET/POST | `/projects/{id}/evidence/...` | Evidence |
| POST | `/projects/{id}/business-verdicts/...` | Verdict |
| POST | `/projects/{id}/launch-pack/...` | Launch Pack |
| POST | `/projects/{id}/offers/...` | Offer Builder |
| POST | `/projects/{id}/publication-packages/...` | Package |
| POST | `/projects/{id}/publishing/.../execute` | Publish (gated) |
| POST | `/media-generation/video-smoke/execute` | Video smoke |

Exact paths — inspect route files or OpenAPI at `/docs` when server running.

---

## Contracts & versioning

- All request/response types in `app/schemas/contracts.py`
- New entities: **contracts first** → DB → API
- StrEnum for status fields — no magic strings in handlers
- Breaking changes require migration + test updates

---

## External integrations (via services)

| Service | Config |
|---------|--------|
| LLM | `app/core/config.py` |
| Telegram | Bot token in `.env` |
| Redis | Optional session/cache |
| OpenAI Images | `MEDIA_GENERATION_ENABLED` |
| Higgsfield | CONN-HF gates |

Never hardcode secrets.

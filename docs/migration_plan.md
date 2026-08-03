# Migration plan (Node / n8n → Python)

## Phase 0 — Foundation (current)

- [x] Project structure, tooling (uv, ruff, mypy, pytest, pre-commit)
- [x] FastAPI skeleton: `/health`, `/version`, `/webhooks/telegram`
- [x] Settings, structlog, PII stub, Telegram secret check
- [x] Data contracts in `app/schemas/contracts.py`

## Phase 1 — Persistence (done)

- [x] SQLModel tables mirroring contracts
- [x] Alembic migrations (`20260529_0001_initial_tables`)
- [x] Redis client + health checks
- [x] Repository layer (user, project, task, memory)

## Phase 1.1 — CRUD API (done)

- [x] `app/api/deps.py` — `get_session` dependency
- [x] CRUD routers: `/users`, `/projects`, `/tasks`, `/memory`
- [x] PATCH schemas in `app/schemas/crud.py`
- [x] API tests (25 total with foundation)

## Phase 2 — Integrations

- Telegram outbound client
- LiteLLM + budget routing
- Langfuse traces

## Phase 3 — Agents

- LangGraph orchestrator
- Marketing pipeline
- Workflow catalog from `knowledge_base`

## Phase 4 — SaaS

- Multi-tenant projects
- Billing (BFT)
- Stripe / plans

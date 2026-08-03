# BotFazer — Architecture (foundation)

## Principles

1. **Contracts first** — all entities live in `app/schemas/contracts.py` before DB or agents.
2. **No agent logic in foundation** — LangGraph, LiteLLM, Langfuse arrive in later phases behind services.
3. **Security by default** — every inbound payload passes PII sanitization; logs never store raw PII.
4. **Configuration via environment** — `pydantic-settings` only; no secrets in code.

## Layers

```
┌─────────────────────────────────────────┐
│  API (FastAPI routers)                  │
│  health, webhooks, future REST v1       │
├─────────────────────────────────────────┤
│  Domain (users, projects, agents, mem)  │
├─────────────────────────────────────────┤
│  Services (llm, telegram, marketing)    │
├─────────────────────────────────────────┤
│  DB (SQLModel + PostgreSQL)             │
│  Workers (async jobs)                   │
└─────────────────────────────────────────┘
```

## Request flow (Telegram webhook, current)

1. `POST /webhooks/telegram`
2. Verify `X-Telegram-Bot-Api-Secret-Token`
3. Parse JSON → `sanitize_payload`
4. Acknowledge `{ "status": "accepted" }` (no downstream processing yet)

## Planned integrations

| Component | Phase |
|-----------|-------|
| PostgreSQL + Alembic | 2 |
| Redis session memory | 2 |
| LiteLLM | 3 |
| LangGraph orchestrator | 3 |
| Langfuse | 3 |
| Presidio PII | 3 |

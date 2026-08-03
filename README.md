# Marketsynth AI Context (sanitized mirror)

Architecture / SoT / structure backup for recovery. **Not** a production deploy repo.

Secrets are excluded or replaced with `<REDACTED>` / empty placeholders. Copy `.env.example` → `.env` and fill locally.

Source snapshot task: **REPO-SNAPSHOT-01**.

---

# Marketsynth

> Official product name: **Marketsynth**.  
> **BotFazer** was the former internal working name. Legacy package/path/env identifiers remain until a controlled migration.

SaaS-платформа ИИ-агентов для маркетинга. **Phase 2** закрывает LLM + read-only tools (envelope, audit, dry-run executor). LangGraph и write-tools — Phase 3+.

Подробная архитектура Phase 2: [docs/phase_2_llm_tools.md](docs/phase_2_llm_tools.md).  
LangGraph / handoff / outbox runbook: [docs/phase_3_langgraph_handoff.md](docs/phase_3_langgraph_handoff.md).

## Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Быстрый старт

```powershell
cd "C:\Users\Сарбаст\Мой проект\botfazer"
uv sync --extra dev
copy .env.example .env
uv run uvicorn app.main:app --reload
```

Проверка:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/version
- http://127.0.0.1:8000/docs (только в `APP_ENV=development`)

## Internal Operations UI (Phase UI.12 — demo freeze)

Next.js UI в [`web/`](web/): **internal MVP demo** — campaigns → plan → review → asset → schedule. Не публичный SaaS (нет login/billing в UI).

**Документация (тестеры → аналитика):**

1. [docs/ui_demo_script.md](docs/ui_demo_script.md) — сценарий демо  
2. [docs/ui_tester_feedback_template.md](docs/ui_tester_feedback_template.md) — шаблон обратной связи  
3. [docs/ui_troubleshooting.md](docs/ui_troubleshooting.md) — troubleshooting  
4. 10–15 демонстраций → анализ feedback  
5. [UI.13 analytics](docs/ui_13_product_analytics_deferred.md) — **позже** (события `campaign_created`, …)

Также: [ui_demo_readiness_audit.md](docs/ui_demo_readiness_audit.md), [ui_invariants.md](docs/ui_invariants.md), [ui_demo_smoke_checklist.md](docs/ui_demo_smoke_checklist.md)

**Проверка перед показом тестеру:**

```powershell
uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key
cd web
npm run lint
npm run build
```

**Запуск демо:**

```powershell
uv run uvicorn app.main:app --reload
# paste NEXT_PUBLIC_* from seed into web/.env.local
cd web && npm run dev
```

UI: http://localhost:3000 — [web/README.md](web/README.md).

## Smoke seed

Идемпотентный demo-набор (user, project, task, memory) для локальной проверки БД:

```powershell
uv run python scripts/smoke_seed.py
```

Повторный запуск не создаёт дубликаты. При первом запуске в stdout печатается `bfz_...` API key — сохраните его.

## Demo marketing flow (UI.10–UI.12)

Полный набор для демо ops UI (campaign, Telegram channel, plan draft, assets, approved + review + scheduled job):

```powershell
uv run python scripts/seed_demo_marketing_flow.py --reset-db --refresh-api-key
```

В конце печатает `NEXT_PUBLIC_BOTFAZER_PROJECT_ID` и `NEXT_PUBLIC_BOTFAZER_API_KEY` для `web/.env.local`. Аудит: [docs/ui_demo_readiness_audit.md](docs/ui_demo_readiness_audit.md).

## API authentication

Защищённые эндпоинты (`/projects`, `/tasks`, `/memory`, `/auth/api-keys`) требуют заголовок:

```bash
curl -H "Authorization: Bearer bfz_your_api_key_here" http://127.0.0.1:8000/projects
```

Создание API key (нужен уже существующий ключ или smoke seed):

```bash
curl -X POST http://127.0.0.1:8000/auth/api-keys \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Cursor dev key\"}"
```

Plain key возвращается **только** в ответе `POST /auth/api-keys`. `POST /users` остаётся без auth для bootstrap.

### Agent registry

```bash
# Создать agent в project (Bearer обязателен)
curl -X POST http://127.0.0.1:8000/agents \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\": \"<project-uuid>\", \"type\": \"strategist\"}"

# Список agents текущего user
curl -H "Authorization: Bearer bfz_your_api_key_here" http://127.0.0.1:8000/agents

# Активировать agent
curl -X POST http://127.0.0.1:8000/agents/<agent-uuid>/activate \
  -H "Authorization: Bearer bfz_your_api_key_here"
```

Типы: `strategist`, `researcher`, `copywriter`, `content_planner`, `critic`, `analyst`, `orchestrator`.

### Agent runs (logging skeleton)

```bash
# Создать run (без LLM — только журнал)
curl -X POST http://127.0.0.1:8000/agent-runs \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"<agent-uuid>\", \"input_payload\": {}, \"metadata\": {}}"

# Отметить running → succeeded
curl -X POST http://127.0.0.1:8000/agent-runs/<run-uuid>/running \
  -H "Authorization: Bearer bfz_your_api_key_here"

curl -X POST http://127.0.0.1:8000/agent-runs/<run-uuid>/succeeded \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"output_payload\": {\"result\": \"ok\"}}"

# Список runs (фильтры: project_id, agent_id, task_id, status)
curl -H "Authorization: Bearer bfz_your_api_key_here" \
  "http://127.0.0.1:8000/agent-runs?status=running"
```

### Phase 3 freeze (3.16)

Phase 3 is frozen as the execution/delivery layer before Phase 4. See:

- `docs/phase_3_production_readiness_audit.md` — architecture audit and rollback
- `tests/test_phase_3_invariants.py` — safety rails
- `GET /health/operations` — `config_warnings` for risky env combos

**Rollback to classic:** `AGENT_EXECUTION_FORCE_CLASSIC=true`

**Replay failed AgentRun safely:** `POST /agent-runs/{id}/replay` → `POST /agent-runs/{new_id}/execute` (never reset in-place).

**Debug failed webhook:** `GET /projects/{id}/webhook-deliveries` (URL preview has no query); check outbox status; replay with `POST /projects/{id}/events/{event_id}/replay` if not `sent`.

Optional smoke (local, skip if no API key):

```bash
uv run python scripts/smoke_execute_classic.py
uv run python scripts/smoke_execute_langgraph.py
uv run python scripts/smoke_handoff_outbox_webhook.py
```

### Production execute (Phase 3.13–3.14)

`POST /agent-runs/{id}/execute` — единая точка входа (classic или LangGraph по resolver). Перед запуском run атомарно переводится `queued → running`; повторный execute того же run запрещён (409).

```bash
curl -X POST "http://127.0.0.1:8000/agent-runs/<run-uuid>/execute" \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Idempotency-Key: my-request-id-1"
```

- Заголовок `Idempotency-Key` опционален (до 128 символов, `[a-zA-Z0-9._:-]`).
- Тот же ключ на уже `succeeded` run возвращает существующий результат без повторного исполнения.
- `failed` / `succeeded` run без clone не перезапускаются через `/execute`.
- **AgentRun replay (Phase 3.15):** `POST /agent-runs/{id}/replay` — клонирует failed/cancelled run в новый `queued` (старый run не меняется), затем `POST /agent-runs/{new_id}/execute`. Outbox/handoff replay — отдельные endpoints (см. `docs/phase_3_langgraph_handoff.md`).

Отладка без guard/idempotency: `execute-dry-run` (classic) и `execute-graph-dry-run` (LangGraph).

### Dry-run executor (Phase 2.0 — mock pipeline, без LiteLLM)

```bash
# 1. Создать agent run (status=queued)
curl -X POST http://127.0.0.1:8000/agent-runs \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"<agent-uuid>\", \"input_payload\": {\"prompt\": \"hello\"}, \"metadata\": {}}"

# 2. Прогнать dry-run: queued → running → mock LLM → succeeded
curl -X POST http://127.0.0.1:8000/agent-runs/<run-uuid>/execute-dry-run \
  -H "Authorization: Bearer bfz_your_api_key_here"

# 3. Список LLM requests для run
curl -H "Authorization: Bearer bfz_your_api_key_here" \
  "http://127.0.0.1:8000/llm-requests?agent_run_id=<run-uuid>"

# 4. LLM request с response
curl -H "Authorization: Bearer bfz_your_api_key_here" \
  http://127.0.0.1:8000/llm-requests/<request-uuid>

# 5. Проверить agent run succeeded
curl -H "Authorization: Bearer bfz_your_api_key_here" \
  http://127.0.0.1:8000/agent-runs/<run-uuid>
```

### LLM provider config (Phase 2.3)

По умолчанию dry-run использует **mock** — API-ключи не нужны.

```bash
# .env — глобальные defaults и секреты провайдеров
DEFAULT_LLM_PROVIDER=mock
DEFAULT_LLM_MODEL=mock-model
OPENAI_API_KEY=sk-...

# agent.config — только provider/model/temperature/max_tokens
curl -X PATCH http://127.0.0.1:8000/agents/<agent-uuid> \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"config\": {\"llm\": {\"provider\": \"openai\", \"model\": \"gpt-4o-mini\", \"temperature\": 0.2}}}"
```

Правила:

- Секреты (`api_key`, `token`, `secret`, `credentials`) **запрещены** в `agent.config` — только в `.env` / Settings.
- Для OpenAI: задайте `OPENAI_API_KEY` и `agent.config.llm.provider=openai`.
- `LLMRequest` / `LLMResponse` не хранят ключи; pytest не делает реальных LLM-вызовов.

### Manual LiteLLM smoke test (Phase 2.4)

**Внимание:** команда делает **реальный платный** API-вызов OpenAI. Не входит в pytest и не трогает dry-run/mock контур.

1. Задайте ключ в `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
```

2. Установите LiteLLM (optional extra) и запустите smoke:

```powershell
uv sync --extra llm
uv run python scripts/smoke_litellm_openai.py
```

3. Успешный результат — exit code `0` и stdout примерно такой:

```text
provider: openai
model: gpt-4o-mini
content: LiteLLM smoke ok
usage: input_tokens=..., output_tokens=..., total_tokens=...
```

4. Без `OPENAI_API_KEY` команда завершится с кодом `1` и понятной ошибкой. Секреты, `raw_response` и полный `Settings` в вывод **не** попадают.

### LLM timeout and retry (Phase 2.5)

Настройки берутся из `.env`:

- `LLM_TIMEOUT_SECONDS` — верхняя граница ожидания одной попытки
- `LLM_MAX_RETRIES` — число **дополнительных** retry после первой неудачи

Retryable ошибки (exponential backoff + jitter):

- timeout
- rate limit
- temporary provider unavailable

**Не** retry:

- authentication / missing API key
- bad request / invalid payload

Ошибки нормализуются в доменные `LLMError` с безопасным сообщением без секретов. Executor и dry-run mock по-прежнему работают без реальных ключей.

### LLM observability (Phase 2.6)

Сейчас для каждого LLM-вызова фиксируем:

- `provider`, `model`
- `latency_ms`, `retry_count`
- `prompt_tokens`, `completion_tokens`, `total_tokens`
- `estimated_cost_usd` — **placeholder (`null`)**, реальные цены позже
- `error_type`, `safe_message` при ошибках

Структурированные события: `llm.call.started`, `llm.call.succeeded`, `llm.call.failed`, `llm.call.retry`.

**Не логируем и не сохраняем:**

- API keys / secrets / Settings / `.env`
- raw provider response (`raw_response` в БД пустой)
- полные prompts/messages в metadata (они остаются в `LLMRequest.input_payload`)

Langfuse SDK будет подключён позже как внешний приёмник метрик.

### Prompt/message builder (Phase 2.7)

Сборка LLM messages вынесена в `app/prompts/`:

- `build_llm_messages()` — system + optional memory + user messages
- `templates.py` — короткие default system prompts по `AgentType`
- `safety.py` — блокировка секретов в prompt context

Executor не знает деталей prompt-логики; в БД сохраняется metadata (`prompt_template_id`, `message_count`), а не полный dump messages.

### Agent tool contracts skeleton (Phase 2.8)

Слой `app/tools/` готовит function calling **без реального execution**:

- `contracts.py` — `ToolDefinition`, `ToolCall`, `ToolResult`, `ToolExecutionContext`
- `registry.py` — allow-list registry (`register`, `get`, `list_for_agent`, `validate_tool_allowed`)
- `security.py` — запрет секретов в tool arguments, redaction результатов
- `errors.py` — доменные `ToolError` с `safe_message`

**Сейчас не делаем:**

- tool execution loop
- real function calling через LiteLLM
- LangGraph / MCP / web search / Telegram / file / DB tools

Dry-run executor только добавляет `tools_metadata` в `LLMRequest.request_metadata` (`tools_enabled`, `tool_count`, `tool_names`). Tool calls не выполняются, second LLM call не делается.

**Phase 2.9** — parsing tool_calls от модели + safe no-op executor (status `skipped`).

### Tool call parsing + safe no-op executor (Phase 2.9)

Контур function calling обкатан **без реального execution**:

- `parser.py` — `parse_tool_calls()` из OpenAI-like формата (`function.name`, JSON/dict arguments)
- `executor.py` — `SafeNoOpToolExecutor` возвращает `skipped` (`tool_execution_disabled`) или safe `failed`
- `MockLLMAdapter` — тестовый режим через `mock_tool_call` / `debug_tool_call` в `input_payload`
- `LiteLLMAdapter` — читает `tool_calls` из response, но **не** передаёт tools в provider (Phase 2.10)

Executor после LLM:

- прогоняет tool calls через no-op executor
- пишет `tools_metadata` (`tool_calls_detected`, `tool_calls_executed=0`, `tool_calls_skipped`)
- **не** делает second LLM call
- run остаётся `succeeded`, если LLM-вызов успешен

### Tool definitions in provider (Phase 2.10)

Флаг `TOOLS_PROVIDER_ENABLED=false` по умолчанию.

- `false` — tool definitions **не** передаются в LiteLLM/OpenAI; registry и `tools_metadata` работают
- `true` — `LiteLLMAdapter` конвертирует tools через `app/tools/openai_schema.py` и передаёт `tools` + `tool_choice=auto`
- execution по-прежнему **no-op** через `SafeNoOpToolExecutor`; second LLM call нет

```bash
# .env
TOOLS_PROVIDER_ENABLED=false
```

### Phase 2 complete (LLM tools layer)

- **Dry-run executor** — LLM #1 → tool round → LLM #2 (`AgentRunExecutor`)
- **Read-only tools** — `memory.search`, `project_context.get`, `task.get`, `task.list_recent`, plus Phase 4.1 marketing reads (`marketing_brief.*`, `content_asset.*`)
- **ToolResultEnvelope** — unified `ok` / `data` / `error` / `meta`
- **Audit** — `tool_execution_logs` + API filters + `output_payload.tools` summary
- **Guards** — permission matrix, agent allowlists, argument validator, per-round and total byte limits

```powershell
# Real OpenAI tool round (skips without OPENAI_API_KEY)
uv run python scripts/smoke_litellm_tools.py

# LangGraph dry-run path (parallel to classic executor)
curl -X POST http://127.0.0.1:8000/agent-runs/<run-uuid>/execute-graph-dry-run \
  -H "Authorization: Bearer bfz_your_api_key_here"
```

### Tool permission matrix (Phase 2.11)

`app/tools/permissions.py` — централизованная матрица `agent_type → allowed/denied tools`:

- `ToolExecutionMode`: `disabled`, `no_op`, `read_only`, `write`
- `DEFAULT_TOOL_PERMISSION_MATRIX` — policy per `AgentType`
- `filter_tools_for_agent()` / `assert_tool_allowed()` — allow-list + deny write tools

`tools_metadata.permission_policy` логирует `agent_type`, `execution_mode`, `allowed_tool_count`.

### Real read-only tool: memory.search (Phase 2.12)

Первый **реальный** tool execution — только `memory.search` через explicit allow-list `REAL_READ_ONLY_EXECUTABLE_TOOLS`.

- `MemorySearchToolExecutor` — text search через `MemoryService.search()` (SQL `LIKE`, без embeddings)
- scope: `owner_id` + `project_id`
- arguments: `query` (required), optional `limit` (default 5, max 20 clamped)
- write tools по-прежнему `tool_not_allowed`
- `tools_metadata.tool_executions` — compact summary (`result_count`, без full content dump)

**Phase 2.13** — tool result injection обратно в LLM messages.

### LLM request logging (skeleton, без провайдера)

```bash
# Создать LLM request для agent run
curl -X POST http://127.0.0.1:8000/llm-requests \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"agent_run_id\": \"<run-uuid>\", \"provider\": \"mock\", \"model\": \"mock-gpt\", \"input_payload\": {}}"

# Отметить running → succeeded (создаёт llm_response)
curl -X POST http://127.0.0.1:8000/llm-requests/<request-uuid>/running \
  -H "Authorization: Bearer bfz_your_api_key_here"

curl -X POST http://127.0.0.1:8000/llm-requests/<request-uuid>/succeeded \
  -H "Authorization: Bearer bfz_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"output_payload\": {\"text\": \"hello\"}, \"input_tokens\": 10, \"output_tokens\": 5, \"total_tokens\": 15}"

# Список LLM requests (фильтры: project_id, agent_id, agent_run_id, status, provider, model)
curl -H "Authorization: Bearer bfz_your_api_key_here" \
  "http://127.0.0.1:8000/llm-requests?provider=mock&status=succeeded"
```

## Тесты и качество

```powershell
uv run pytest
uv run ruff check app tests
uv run mypy app
uv run pre-commit install
```

## Phase 4.0 — Marketing domain

Склад маркетинговых артефактов (без подключения к агентам и LangGraph):

- **Marketing brief** — продукт, аудитория, оффер, цели, ограничения
- **Content asset** — лендинг, пост, email, ad copy и др.

```bash
curl -X POST "http://127.0.0.1:8000/projects/<project-id>/marketing-briefs" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"title":"Q2 Launch","product_description":"...","goals":["leads"]}'

curl -X POST "http://127.0.0.1:8000/projects/<project-id>/content-assets" \
  -H "Authorization: Bearer bfz_..." \
  -H "Content-Type: application/json" \
  -d '{"type":"telegram_post","title":"Launch","body":"..."}'
```

Подробнее: [docs/phase_4_marketing_domain.md](docs/phase_4_marketing_domain.md)

## Phase 4.1 — Marketing read-only tools

Восемь marketing/funnel read-only executors (всего **12** real read-only tools с task/memory):

- `marketing_brief.get` / `marketing_brief.list`
- `content_asset.get` / `content_asset.list`
- `marketing_funnel.get` / `marketing_funnel.list` / `marketing_funnel.step_assets` / `marketing_funnel.gap_analysis`

Полный `body` только при `include_body=true` (до 4 000 символов); иначе только `body_preview`.

## Phase 4.2 — Agent write safety gate (`content_asset.create_draft`)

Первый agent write-tool — **выключен по умолчанию**:

```env
AGENT_WRITE_TOOLS_ENABLED=false
AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED=false
AGENT_WRITE_TOOL_BODY_MAX_CHARS=12000
```

При `true` + `true`: copywriter, content_planner, critic, researcher, strategist, orchestrator могут создавать asset только в **`draft`**. LLM не видит tool, пока флаги выключены. Полный `body` не возвращается в result/audit preview.

Подробнее: [docs/phase_4_marketing_domain.md](docs/phase_4_marketing_domain.md)

## Phase 4.3 — Human approval workflow

Жизненный цикл content asset: **draft → approved → archived**.

- `POST /projects/{id}/content-assets/{asset_id}/approve` — только из `draft`
- `POST /projects/{id}/content-assets/{asset_id}/archive` — из `draft` или `approved` (409 если уже archived)
- Агент по-прежнему только `content_asset.create_draft` (status=draft)
- События outbox: `content_asset.approved`, `content_asset.archived`

## Phase 4.4 — Content asset versioning

История версий `title` / `body` / `metadata`: каждая правка в **draft** создаёт новую версию; **approve** фиксирует `approved_version_number = current_version_number`. Утверждённый контент **нельзя** менять через `PATCH`. API: `GET .../content-assets/{id}/versions` и `.../versions/{n}`.

## Phase 4.5 — Revision from approved

`POST .../content-assets/{id}/create-revision` — новый **draft** asset на базе approved snapshot (поля `source_asset_id`, `source_version_number`, `revision_number`). Исходный approved asset не меняется. Это revision branch, не rollback.

## Phase 4.6 — Content asset diff (read-only)

Сравнение перед approve: version diff, asset diff, revision-diff. Unified body diff (до 300 строк), metadata diff без secret-ключей. Без apply-diff.

## Phase 4.8 — Marketing funnel skeleton

Funnels, ordered steps, and content-asset links per step (`/projects/{id}/funnels/...`). Draft и approved assets можно привязать к шагу.

## Phase 4.9 — Marketing funnel read tools

Агенты читают воронку и customer journey (read-only):

- `marketing_funnel.get` — воронка + шаги (`include_steps`)
- `marketing_funnel.list` — список воронок
- `marketing_funnel.step_assets` — assets на шаге
- `marketing_funnel.gap_analysis` — эвристика: missing steps, steps без assets, **coverage score** `(8 − missing) / 8`

Copywriter: только `get` + `step_assets`. Strategist / analyst / content_planner: все четыре. Подробнее: [docs/phase_4_marketing_domain.md](docs/phase_4_marketing_domain.md).

## Phase 5.0 — Marketing strategist agent MVP

Первый **продуктовый** агент: strategist читает brief/funnel/assets, запускает `marketing_funnel.gap_analysis`, при включённых write-флагах создаёт draft через `content_asset.create_draft` (без approve).

```env
AGENT_WRITE_TOOLS_ENABLED=true
AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED=true
```

Пример `input_payload` для run: `brief_id`, `funnel_id`, `goal`. Workflow и mock `mock_strategy_flow`: [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md).

## Phase 5.1 — Strategy draft quality + smoke

Heuristic quality contract для strategy draft (`metadata.quality`, score 0–1). Низкий score **не блокирует** создание draft и **не** auto-approve.

- `GET /projects/{id}/content-assets/{asset_id}/quality` — read-only оценка
- Smoke: `uv run python scripts/smoke_marketing_strategist.py` (нужен `BOTFAZER_API_KEY` / `SMOKE_API_KEY`)

## Phase 5.2 — Copywriter Agent MVP

Второй продуктовый агент: copywriter читает brief / source asset / funnel step через tools и создаёт **только draft** (`email`, `ad_copy`, `telegram_post`, `landing_page`) через `content_asset.create_draft`. Без approve/publish.

```json
{
  "brief_id": "<uuid>",
  "step_id": "<uuid>",
  "source_asset_id": "<uuid>",
  "asset_type": "email",
  "goal": "write launch email"
}
```

Те же write-флаги, что у strategist. Mock: `agent.config.mock_copywriter_flow: true`. Подробнее: [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md).

## Phase 5.3 — Content Planner Agent MVP

Третий продуктовый агент: читает brief/funnel/assets, запускает `marketing_funnel.gap_analysis`, создаёт **draft** content plan (`article`, `purpose: content_plan`). Не линкует assets к шагам воронки.

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "goal": "plan content for launch funnel"
}
```

Mock: `agent.config.mock_content_planner_flow: true`. Отличие от strategist — план производства по шагам; от copywriter — не пишет channel copy. [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md).

## Phase 5.4 — Critic Agent MVP

Агент контроля качества: читает `source_asset_id`, brief/funnel; создаёт **отдельный** review draft (`purpose: content_review`). Исходный asset **не меняется**, approve — только человек.

```json
{
  "source_asset_id": "<uuid>",
  "brief_id": "<uuid>",
  "goal": "review this copy before approval"
}
```

Mock: `agent.config.mock_critic_flow: true`. Write-флаги как у других marketing-агентов; critic добавлен в allowlist `content_asset.create_draft`. [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md).

## Phase 5.5 — Researcher Agent MVP

Внутренний исследователь: brief/assets/funnel/memory → **draft** research memo (`purpose: research_draft`). Без веб-поиска; непроверенные выводы помечать как assumptions / requires external validation.

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "research_topic": "audience objections",
  "goal": "prepare internal research memo"
}
```

Mock: `agent.config.mock_researcher_flow: true`. [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md).

## Phase 5.6 — Orchestrator Agent MVP

Супервайзер: читает контекст (brief/funnel/assets), **маршрутизирует** к specialist-агентам и **делегирует** через LangGraph handoff (`handoff_to_agent_id` / `handoff_target_agent_type`). Не подменяет работу copywriter/planner/strategist/researcher/critic.

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "goal": "coordinate launch content",
  "handoff_target_agent_type": "content_planner"
}
```

`orchestration.default_inline_child_execution: false` — дочерний run в очереди Redis; inline только с `handoff_execute_child: true` + `GRAPH_HANDOFF_EXECUTE_CHILD=true`. Для orchestrator в проде рекомендуется **LangGraph** (`execution_engine: langgraph`). Classic dry-run handoff не выполняет.

Mock: `agent.config.mock_orchestrator_flow: true` (авто-роутинг по `goal` на gate). [docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md), [docs/phase_3_langgraph_handoff.md](docs/phase_3_langgraph_handoff.md).

## Phase 5.7 — Marketing workflow E2E smoke

Сквозной сценарий: **orchestrator** → handoff → **content_planner** (draft plan) → **critic** (review draft) → **ручной** approve. Регрессия: `tests/test_marketing_workflow_e2e.py`. Локальный smoke: `scripts/smoke_marketing_workflow.py` (без ключа — safe skip; `--approve-draft` только по флагу). Сводка для UI: `GET /agent-runs/{id}/workflow-summary`.

```bash
uv run python scripts/smoke_marketing_workflow.py
```

[docs/phase_5_marketing_agents.md](docs/phase_5_marketing_agents.md)

## Phase 5.8 — Product readiness freeze

Phase 5 MVP **заморожен**: orchestrator → specialists → draft → critic review → **ручной** approve. Аудит: [docs/phase_5_product_readiness_audit.md](docs/phase_5_product_readiness_audit.md). Матрица инструментов: `GET /agents/tool-matrix`. Инварианты: `tests/test_phase_5_agent_invariants.py`. Smoke: `scripts/smoke_phase_5_agents.py`.

```bash
uv run pytest tests/test_phase_5_agent_invariants.py tests/test_marketing_workflow_e2e.py
uv run python scripts/smoke_phase_5_agents.py
```

## Phase 6.0 — Publishing layer skeleton

HTTP-only очередь публикации **approved** assets в каналы (`webhook`, `telegram`, `email`, `tilda`, `custom`). Без внешней отправки и без agent tools.

- Approve — по-прежнему только человек (`POST .../content-assets/{id}/approve`)
- Каналы: `POST/GET/PATCH/DELETE /projects/{id}/publishing-channels` (`config_preview` без секретов)
- Jobs: `POST/GET /projects/{id}/publication-jobs`, cancel queued: `POST .../publication-jobs/{id}/cancel`
- Job фиксирует `asset_version_number = approved_version_number`

Документация: [docs/phase_6_publishing.md](docs/phase_6_publishing.md). Тесты: `tests/test_publishing_layer.py`.

```bash
uv run pytest tests/test_publishing_layer.py
```

## Phase 6.1 — Publication worker + delivery logs

Worker обрабатывает `queued` jobs через mock dispatcher (без внешнего HTTP). `custom` → noop success; остальные типы каналов → skipped adapter + failed job. Delivery logs: `GET /projects/{id}/publication-deliveries`. Ручной drain: `POST /projects/{id}/publication-jobs/process`. Scheduler: `PUBLICATION_WORKER_ENABLED=false` по умолчанию.

[docs/phase_6_publishing.md](docs/phase_6_publishing.md) · `tests/test_publication_worker.py`

## Phase 6.2 — Real webhook publishing adapter

`PublishingChannelType.webhook` отправляет **approved asset version** на URL пользователя (POST JSON + optional HMAC). `custom` noop без изменений; telegram/email/tilda — unsupported. Config: `url`, optional `signing_secret`, optional `headers`. Retry на non-2xx/timeout до `PUBLICATION_JOB_MAX_ATTEMPTS`.

[docs/phase_6_publishing.md](docs/phase_6_publishing.md) · `tests/test_publication_webhook_adapter.py`

## Phase 6.3 — Publication replay + metrics

Replay `failed`/`cancelled` jobs → `queued` (без auto-dispatch). `POST .../publication-jobs/{id}/replay`, `POST .../publication-jobs/replay-batch`. Метрики в `operational-metrics` (`publishing` block). `GET /health/operations` → `pending_publication_jobs_count`.

Workflow: replay → `POST .../publication-jobs/process`.

[docs/phase_6_publishing.md](docs/phase_6_publishing.md) · `tests/test_publication_replay_metrics.py`

## Phase 6.4 — Publishing production readiness freeze

Publishing layer **заморожен** после webhook/replay/metrics: approved-only queue, worker, webhook adapter, replay без auto-dispatch. **Без** новых внешних адаптеров (Telegram/Tilda/email) в этом freeze.

- Аудит: [docs/phase_6_publishing_readiness_audit.md](docs/phase_6_publishing_readiness_audit.md)
- Инварианты: `tests/test_phase_6_publishing_invariants.py`
- Smoke (safe skip без API key; `WEBHOOK_TEST_URL` для реального webhook): `scripts/smoke_publication_webhook.py`
- Config warnings на `GET /health/operations`: `publication_worker_enabled_without_database`, `publication_job_max_attempts_lt_1`, `publication_delivery_timeout_invalid`, `publication_worker_interval_too_low`

Replay workflow: `POST .../replay` → `POST .../publication-jobs/process`. Агенты **не** могут queue/publish/approve — только человек через HTTP.

```bash
uv run pytest tests/test_phase_6_publishing_invariants.py
uv run python scripts/smoke_publication_webhook.py
```

[docs/phase_6_publishing.md](docs/phase_6_publishing.md)

## Phase 7 — Telegram publication adapter

Telegram — первый production publishing adapter. Поверх freeze-слоя публикации:

- **7.0** — `sendMessage` text-only, approved-only, pinned version.
- **7.1** — `sendPhoto` с remote media URL (`media_url`/`image_url` в approved version metadata), caption по body.
- **7.2** — readiness audit + config sanity + smoke.

Env:

- `TELEGRAM_PUBLICATION_ENABLED=false` (по умолчанию)
- `TELEGRAM_PUBLICATION_BOT_TOKEN` — Bot API token (только env/settings)
- `TELEGRAM_PUBLICATION_TIMEOUT_SECONDS` — timeout Telegram вызовов
- `TELEGRAM_PUBLICATION_CHAT_ID` — канал/чат для smoke
- `TELEGRAM_PUBLICATION_SMOKE_MODE=text|photo`
- `TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL` — media URL для photo smoke

Smoke:

```bash
# text-only smoke
export TELEGRAM_PUBLICATION_ENABLED=true
export TELEGRAM_PUBLICATION_BOT_TOKEN=...
export TELEGRAM_PUBLICATION_CHAT_ID=-100...
uv run python scripts/smoke_publication_telegram.py

# photo smoke
export TELEGRAM_PUBLICATION_SMOKE_MODE=photo
export TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL=https://example.com/photo.jpg
uv run python scripts/smoke_publication_telegram.py
```

Ограничения:

- Нет agent tools для Telegram publish.
- Caption для photo ≤1024, иначе `caption_too_long` (skipped).
- Media URL только remote HTTP/HTTPS; URL с секретами в query отвергается до HTTP-вызова.
- Переигрывать можно только `failed`/`cancelled` jobs; `succeeded` никогда не replay-ятся.

Аудит: [docs/phase_7_telegram_publication_readiness_audit.md](docs/phase_7_telegram_publication_readiness_audit.md).

## Phase 8.0 — Scheduled publication jobs

Планирование публикаций без внешнего cron: job может быть создан как `scheduled` и будет переведён в `queued` самим воркером, когда наступит время.

- UTC-only: `scheduled_at` должен быть timezone-aware (`...Z`), naive datetime запрещён.
- `scheduled_at` обязателен для `scheduled`, и должен быть в будущем.
- Replay не восстанавливает schedule: всегда → `queued`. Replay `scheduled` запрещён (`409`).

Документация: [docs/phase_8_publication_scheduling.md](docs/phase_8_publication_scheduling.md)

```bash
uv run pytest tests/test_publication_scheduling.py
```

## Phase 8.3 — Scheduling operational metrics

Scheduling состояние отображается в:

- `GET /projects/{id}/operational-metrics`
- `GET /me/operational-metrics`

В `publishing` block:

- `scheduled_jobs_count`
- `due_scheduled_jobs_count`
- `next_scheduled_publication_at`
- `cancelled_scheduled_jobs_24h`

```bash
uv run pytest tests/test_publication_scheduling_metrics.py
```

## Phase 8.4 — Scheduling readiness audit (freeze)

Audit doc:

- `docs/phase_8_scheduling_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_phase_8_scheduling_invariants.py
uv run pytest tests/test_publication_scheduling.py
uv run pytest tests/test_publication_scheduling_actions.py
uv run pytest tests/test_publication_scheduling_metrics.py
```

## Phase 9.4 — Campaign readiness audit (freeze)

Audit doc:

- `docs/phase_9_campaigns_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_marketing_campaigns.py
uv run pytest tests/test_campaign_binding.py
uv run pytest tests/test_campaign_overview.py
uv run pytest tests/test_campaign_metrics.py
uv run pytest tests/test_phase_9_campaigns_invariants.py
```

## Phase 10.3 — Campaign planner tools readiness audit (freeze)

Agents may **read campaign context** and **save plan drafts** only — no content assets, publication jobs, approve, publish, or schedule via tools.

Audit doc:

- `docs/phase_10_campaign_planner_tools_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_campaign_readonly_tools.py
uv run pytest tests/test_campaign_plan_drafts.py
uv run pytest tests/test_campaign_plan_draft_create_tool.py
uv run pytest tests/test_phase_10_campaign_planner_invariants.py
```

Write flags (both required for `campaign_plan_draft.create`):

```env
AGENT_WRITE_TOOLS_ENABLED=true
CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true
```

## Phase 11.2 — Plan draft asset generation readiness audit (freeze)

Mechanical `generate-assets` from plan drafts — draft content assets only, no LLM, no jobs, idempotent HTTP.

Audit doc:

- `docs/phase_11_plan_draft_assets_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_plan_draft_generate_assets.py
uv run pytest tests/test_plan_draft_generate_assets_idempotency.py
uv run pytest tests/test_phase_11_plan_draft_assets_invariants.py
```

Not in this freeze: agent tool `campaign_plan_draft.generate_assets` (bulk asset creation — higher risk than plan draft save).

## Phase 12.2 — Asset revision tools readiness audit (freeze)

Agents may **read** campaign content assets and create **draft revisions** only — no approve, publish, schedule, or publication jobs via tools.

Audit doc:

- `docs/phase_12_asset_revision_tools_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_campaign_asset_read_tools.py
uv run pytest tests/test_content_asset_create_revision_tool.py
uv run pytest tests/test_phase_12_asset_revision_invariants.py
```

Flags for write revisions (both required):

```bash
AGENT_WRITE_TOOLS_ENABLED=true
CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED=true
```

Not in this freeze: agent `content_asset.approve` / publish / schedule tools (human approval remains the product boundary).

## Phase 13.2 — Campaign workflow readiness audit (freeze)

Agents and the HTTP API expose a **read-only** campaign execution workflow (state + counts + next recommended action). No bulk generate-assets tool, no approve/publish/schedule, no persisted workflow state in DB.

Audit doc:

- `docs/phase_13_campaign_workflow_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_campaign_workflow.py
uv run pytest tests/test_campaign_workflow_tool.py
uv run pytest tests/test_phase_13_campaign_workflow_invariants.py
```

Not in this freeze: agent `campaign_plan_draft.generate_assets` (bulk write), approve/publish/schedule agent tools, DB persistence of `CampaignWorkflowState`.

## Phase 14.3 — Review Queue readiness audit (freeze)

Human review queue (HTTP + `review_queue.list`) and workflow integration via `pending_review_assets` / `human_review_required`. No agent approve/publish/schedule.

Audit doc:

- `docs/phase_14_review_queue_readiness_audit.md`

Freeze checklist:

```bash
uv run pytest tests/test_review_queue.py
uv run pytest tests/test_review_queue_tool.py
uv run pytest tests/test_campaign_workflow.py
uv run pytest tests/test_campaign_workflow_tool.py
uv run pytest tests/test_phase_14_review_queue_invariants.py
```

Not in this freeze: `review_queue.approve`, agent approval/publish/schedule tools, review-queue write APIs.

## Phase AI.4 — Agent chat plan-draft readiness audit (freeze)

Agent chat (`/agents/chat`): advisory workflow context (AI.2) and **one** gated write — `campaign_plan_draft.create` only (AI.3). No bulk generate-assets, approve, schedule, or publish via chat.

Audit doc:

- `docs/phase_ai_4_agent_chat_plan_draft_readiness_audit.md`

Required flags (all `true` for chat tools):

- `AGENT_WRITE_TOOLS_ENABLED`
- `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED`
- `AGENT_CHAT_TOOLS_ENABLED`
- `TOOLS_PROVIDER_ENABLED`

Freeze checklist:

```bash
uv run pytest tests/test_agent_chat.py
uv run pytest tests/test_agent_chat_workflow_context.py
uv run pytest tests/test_agent_chat_plan_draft_tool.py
uv run pytest tests/test_phase_ai_4_agent_chat_plan_draft_invariants.py
```

## Phase AI.5 — Agent chat generate assets from plan draft (freeze)

Chat may call `campaign_plan_draft.generate_assets` (orchestrator / content_planner only) when all flags are on. Uses the same service as HTTP `POST .../generate-assets`. No approve, schedule, or publish.

Required flags:

- `AGENT_WRITE_TOOLS_ENABLED`
- `CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED`
- `AGENT_CHAT_TOOLS_ENABLED`
- `TOOLS_PROVIDER_ENABLED`

Plan draft create in chat still requires `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED` separately.

```bash
uv run pytest tests/test_agent_chat_generate_assets_tool.py
uv run pytest tests/test_agent_chat_plan_draft_tool.py
uv run pytest tests/test_phase_ai_4_agent_chat_plan_draft_invariants.py
```

Not in this freeze: chat approve/publish/schedule, any write beyond plan draft create + generate assets.

## Phase AI.6 — Agent chat bulk-write readiness audit (freeze)

Chat may create **plan drafts** (AI.3) and **draft assets from plan** (AI.5). Approve, schedule, publish, and publication jobs remain human/UI only.

Audit doc:

- `docs/phase_ai_6_agent_chat_generate_assets_readiness_audit.md`

Generate-assets flags (all `true`):

- `AGENT_WRITE_TOOLS_ENABLED`
- `CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED`
- `AGENT_CHAT_TOOLS_ENABLED`
- `TOOLS_PROVIDER_ENABLED`

Plan draft create still requires `CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED` separately.

```bash
uv run pytest tests/test_agent_chat.py
uv run pytest tests/test_agent_chat_workflow_context.py
uv run pytest tests/test_agent_chat_plan_draft_tool.py
uv run pytest tests/test_agent_chat_generate_assets_tool.py
uv run pytest tests/test_phase_ai_6_agent_chat_generate_assets_invariants.py
```

Not in this freeze: chat approve/schedule/publish; agent-assisted revision (see AI.7.1).

## Phase AI.7 — Agent chat content revision

Chat may call `content_asset.create_revision` (copywriter / content_planner / orchestrator) to improve draft or approved-source content. Uses `apply_agent_content_revision` — no approve, schedule, publish, or archive.

Required flags:

- `AGENT_WRITE_TOOLS_ENABLED`
- `CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED`
- `AGENT_CHAT_TOOLS_ENABLED`
- `TOOLS_PROVIDER_ENABLED`

Campaign-wide revision guidance: max **20** draft assets per run (`AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS`).

## Phase AI.8 — Campaign-aware copywriter

Before revising content in chat, the copywriter receives a compact **campaign revision context** (max **8 KB**) built from campaign, workflow, latest plan draft messaging, approved asset examples, and optional current asset snapshot.

Read tools in the revision chat profile include `marketing_campaign.overview`. Context is injected into the prompt (not a new write tool).

- `app/agents/revision_context.py` — context builder + size trim
- Copywriter prompt rules: campaign tone, key_message, workflow, no invented facts

## Phase AI.8.1 — Campaign-aware revision readiness audit (freeze)

AI.8 improves revision **quality**, not write permissions. Freeze context size, leak boundaries, and unchanged approve/schedule/publish no-go.

- `docs/phase_ai_8_campaign_aware_revision_readiness_audit.md`
- Context ≤ 8 KB; no full `plan_payload`, delivery logs, or channel config in prompt context
- **No new write tools** (still only `content_asset.create_revision`)

```bash
uv run pytest tests/test_campaign_aware_revision_context.py
uv run pytest tests/test_agent_chat_revision_tool.py
uv run pytest tests/test_phase_ai_7_revision_invariants.py
uv run pytest tests/test_phase_ai_8_campaign_aware_revision_invariants.py
```

Not in this freeze: AI.9 orchestrator scenarios (see below).

## Phase AI.9 — Marketing orchestrator scenarios

Scenario detection and **recommended_next_steps** for orchestrator chat when a campaign is selected. Prompt-only coordination — **no new read or write tools**.

- `app/agents/scenarios/` — `MarketingScenarioType`, phrase detector
- `app/agents/scenario_context.py` — workflow-aware step lists
- Orchestrator prompt: marketing coordinator rules when a scenario is detected

## Phase AI.9.1 — Marketing orchestrator readiness audit (freeze)

First **orchestrator behavior** layer (scenario thinking, not tools). Freeze before AI.10 sub-agent registry.

- `docs/phase_ai_9_marketing_orchestrator_readiness_audit.md`
- Five scenarios + workflow fallback; no approve / schedule / publish / auto-execution
- **No new tools or write permissions**

```bash
uv run pytest tests/test_marketing_scenarios.py
uv run pytest tests/test_phase_ai_9_marketing_orchestrator_invariants.py
```

Not in this freeze: AI.10 marketer sub-agent registry (see below).

## Phase AI.10 — Marketer sub-agent registry

Internal **Marketer** structure (architecture 3.2): four personas (`strategist`, `copywriter`, `analyst`, `researcher`) with registry metadata, phrase router, and orchestrator **persona routing** in prompts only.

- `app/agents/marketer/` — contracts, registry, router
- `app/prompts/marketer_subagents.py` — persona prompts
- No child `AgentRun`, LangGraph, handoff, or parallel execution

## Phase AI.10.1 — Marketer sub-agent registry readiness audit (freeze)

Persona routing only — registry + router + orchestrator overlay. **No child runs** until AI.11.

- `docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md`
- Four sub-agents; `allowed_tools` ⊆ mapped `AgentType` profile; overlay **orchestrator-only**
- No approve / publish / schedule in persona tools

```bash
uv run pytest tests/test_marketer_subagent_registry.py
uv run pytest tests/test_phase_ai_10_marketer_subagent_registry_invariants.py
```

Not in this freeze: AI.11 real sub-agent execution (see below).

## Phase AI.11 — Real sub-agent execution (copywriter)

Orchestrator **creates a child `AgentRun`** and runs the project copywriter via classic executor (sequential, one child, no nesting).

- `parent_agent_run_id` on `AgentRun` + migration `20260602_0006`
- `app/agents/marketer/execution.py` — `execute_subagent()` (copywriter only)
- Chat `subagent_execution` + UI «Handled by Copywriter»

## Phase AI.11.1 — Sub-agent execution readiness audit (freeze)

Locks **orchestrator → copywriter** only; natural-language router («Перепиши этот пост»); no LangGraph / handoff / parallel / analyst-strategist-researcher child runs.

- `docs/phase_ai_11_subagent_execution_readiness_audit.md`
- Copywriter intent: phrases + rewrite-verb + content-noun tokens (`app/agents/marketer/router.py`)

```bash
uv run pytest tests/test_subagent_execution.py
uv run pytest tests/test_phase_ai_11_subagent_execution_invariants.py
```

## Phase AI.12 — Researcher sub-agent execution

Second real execution path: orchestrator **creates a child `AgentRun`** for the project researcher (same rules as copywriter).

- `_SUPPORTED_SUBAGENTS`: `copywriter`, `researcher`
- `delegate_subagent` in `AgentChatService` (router-selected supported type)
- Chat `subagent_execution`: `{ "subagent": "researcher", "agent_run_id": "..." }`

## Phase AI.12.1 — Researcher execution readiness audit (freeze)

Locks execution layer with **two** real child agents (`copywriter`, `researcher`); strategist/analyst remain persona-only; sequential / one child / no nesting; no LangGraph / handoff / parallel; no approve / publish / schedule / archive from children.

- `docs/phase_ai_12_researcher_execution_readiness_audit.md`
- Frozen routes: «Исследуй аудиторию» → researcher child; «Перепиши этот пост» → copywriter child
- Frozen disambiguation: «Проанализируй рынок» → **no** sub-agent (`None`, orchestrator only) — not researcher or analyst until a future router change

**Freeze checklist:**

```bash
uv run pytest tests/test_subagent_execution.py
uv run pytest tests/test_phase_ai_12_subagent_execution_invariants.py
```

Not in this freeze: **AI.13** strategist execution (see below).

## Phase AI.13 — Strategist sub-agent execution

Third real execution path: orchestrator **creates a child `AgentRun`** for the project strategist (same sequential rules as copywriter/researcher).

- `_SUPPORTED_SUBAGENTS`: `copywriter`, `researcher`, `strategist`
- Frozen strategist phrases: контент-план, стратегия запуска, позиционирование, оффер, план кампании, …
- «Проанализируй рынок» remains **`None`** (AI.12.1 disambiguation unchanged)

## Phase AI.13.1 — Strategist execution readiness audit (freeze)

Locks **three** real child agents; analyst persona-only; one child per parent; no multi-hop chain (AI.14); no LangGraph / handoff / parallel; no approve / publish / schedule / archive from children.

- `docs/phase_ai_13_strategist_execution_readiness_audit.md`

**Freeze checklist:**

```bash
uv run pytest tests/test_phase_ai_13_strategist_execution.py
uv run pytest tests/test_phase_ai_13_strategist_execution_invariants.py
```

Not in this freeze: **AI.14** multi-subagent chain (see below).

## Phase AI.14 — Multi-subagent sequential chain

Orchestrator may run up to **3** sibling child runs (same `parent_agent_run_id`): linear chains only — no DAG, LangGraph, handoff, or parallel.

- `app/agents/marketer/chains.py` — `CONTENT_LAUNCH`, `CONTENT_PLAN`, `RESEARCH`, `REWRITE`
- `detect_execution_chain()` / `resolve_execution_chain()` in router
- `app/agents/marketer/chain_execution.py` — `compact_subagent_output` (≤ 4 KB handoff between steps)
- Chat: `subagent_chain[]`; UI «Handled by Researcher → Strategist → Copywriter»

```bash
uv run pytest tests/test_subagent_chain_execution.py
```

## Phase AI.14.1 — Multi-subagent chain readiness audit (freeze)

Locks linear chains (≤ 3 sibling children), frozen chain table, compact handoff ≤ 4 KB, `subagent_chain` API, «Проанализируй рынок» = None.

- `docs/phase_ai_14_multi_subagent_chain_readiness_audit.md`

**Freeze checklist:**

```bash
uv run pytest tests/test_subagent_chain_execution.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
```

## Phase AI.15 — General Agent skeleton

Top-level router only — **marketing** delegates to Marketer orchestrator (existing AI.14 chains). No Programmer/Media/Tilda/Email.

- `app/agents/general/` — `contracts`, `router`, `execution`, `prompts`
- `app/agents/run_depth.py` — `MAX_AGENT_RUN_DEPTH = 2` (General → orchestrator → subagents)
- Chat: `general_delegation: { domain, agent_run_id }` + `subagent_chain[]`
- General has **no** tools (routing/delegation only)

```bash
uv run pytest tests/test_general_agent_skeleton.py
```

## Phase AI.15.1 — General Agent readiness audit (freeze)

Locks depth model (`MAX_AGENT_RUN_DEPTH = 2`), marketing-only delegation, empty General tools, no Programmer/Media domains.

- `docs/phase_ai_15_general_agent_readiness_audit.md`

**Freeze checklist:**

```bash
uv run pytest tests/test_general_agent_skeleton.py
uv run pytest tests/test_phase_ai_15_general_agent_invariants.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
```

## Phase AI.16 — Programmer domain skeleton

General routes **programmer** domain to a consultation-only Programmer child (depth 1, no sub-agents). No shell, GitHub, filesystem, deploy, or live bots.

- `app/agents/programmer/` — contracts, prompts, execution
- `AgentType.PROGRAMMER` — empty tool allowlist; `technical_task_draft` in run output (not persisted to DB)

```bash
uv run pytest tests/test_general_programmer_domain.py
```

Not in this phase: repository access, GitHub, file writes, Media/Tilda/Email domains.

## Phase AI.16.1 — Programmer domain readiness audit (freeze)

Locks Programmer as **consultation-only**: depth 1 child, no tools, no children, `technical_task_draft.persisted = false`, no shell/GitHub/filesystem/deploy/secrets.

- `docs/phase_ai_16_programmer_domain_readiness_audit.md`

**Freeze checklist:**

```bash
uv run pytest tests/test_general_programmer_domain.py
uv run pytest tests/test_phase_ai_16_programmer_domain_invariants.py
```

Not in this freeze: GitHub/repo/file-write agent (separate security phase).

## Phase AI.17 — Media domain skeleton

General routes **media** domain to a visual consultant child (depth 1). No image/video generation, Canva/Figma/HeyGen, or file I/O.

- `app/agents/media/` — contracts, prompts, execution
- `visual_brief` in run output with `persisted: false`
- Router priority: telegram bot → programmer; banner for telegram → media; telegram post → marketing

```bash
uv run pytest tests/test_general_media_domain.py
```

Not in this phase: image/video generation APIs, design-tool integrations.

## Phase AI.27 — Marketing orchestrator skeleton

Marketing chat via **orchestrator** or **General → marketing** now returns a `MarketingExecutionPlan` (planning mode only) — no sub-agent child runs, tools, or execute actions in this phase.

- Registry: `MarketingSpecialistType` (6 roles) in `app/agents/marketer/marketing_specialist_registry.py`
- Contract: `MarketingExecutionPlan` in `app/schemas/contracts.py`
- Planning: `app/agents/marketer/planning.py` — `execute_marketer_orchestrator_planning`
- Block type: `marketing_plan` in chat UI

```bash
uv run pytest tests/test_phase_ai_27_marketing_orchestrator_skeleton.py -q
```

Sub-agent chain execution modules remain for AI.28+; chat path does not call them until a later phase enables execution.

## Phase AI.28 — Marketing plan persistence + approval gate

Persist `MarketingExecutionPlan` as first-class artifacts (`marketing_plans` + `marketing_plan_versions`). Chat block action **Save marketing plan** creates `draft` + version 1. Approve/archive via API — no specialist execution yet.

```bash
uv run pytest tests/test_phase_ai_28_marketing_plan_persistence.py -q
```

Endpoints: `GET/POST /projects/{id}/marketing-plans`, `.../approve`, `.../archive`, `.../versions`.

## Phase AI.29 — Marketing plan execution run skeleton

Execution-run entity for **approved** plans only — queued task snapshots from `approved_version_number`, status transitions (`start` → `complete-placeholder`), no specialists/LLM/tools/child `AgentRun`s.

```bash
uv run pytest tests/test_phase_ai_29_marketing_plan_execution_skeleton.py -q
```

- `POST .../marketing-plans/{plan_id}/execution-runs` — create queued run
- `GET .../marketing-plan-execution-runs` — list/filter
- `POST .../start`, `.../complete-placeholder`, `.../cancel`

## Phase AI.30 — Marketing specialist output artifact skeleton

Persisted **specialist output** containers per execution-run task snapshot — placeholder only (no LLM, tools, child `AgentRun`, or `ContentAsset` on approve).

```bash
uv run pytest tests/test_phase_ai_30_marketing_specialist_output_skeleton.py -q
```

- `POST .../marketing-plan-execution-runs/{run_id}/task-outputs/{task_index}/placeholder` — draft output + version 1
- `GET .../marketing-specialist-outputs` — list/filter
- `GET .../{output_id}`, `POST .../approve`, `POST .../archive`, `GET .../versions`

Duplicate active output for the same run + task is idempotent; archived slot blocks re-create (409).

## Phase AI.31 — Strategist specialist dry-run execution

First **real** specialist path — **Strategist only**, one task at a time, no tools, no child `AgentRun`, no `ContentAsset`. Requires **running** execution run and approved plan version snapshot.

```bash
uv run pytest tests/test_phase_ai_31_strategist_specialist_execution.py -q
```

- `POST .../marketing-plan-execution-runs/{run_id}/tasks/{task_index}/execute-specialist`
- Writes `MarketingSpecialistOutput` (`output_type: strategy`) + task `specialist_completed`
- Duplicate active output per task → **409**

## Phase AI.32 — Researcher specialist desk-research execution

**Researcher** only — desk research from approved plan + strategist output. No web search, tools, or `ContentAsset`. Requires strategist task completed or strategist output (draft/approved).

```bash
uv run pytest tests/test_phase_ai_32_researcher_specialist_execution.py -q
```

Reuses `POST .../tasks/{task_index}/execute-specialist`. Without strategist prior → **409** `Researcher requires completed Strategist output`.

## Phase AI.33 — Content Planner specialist dry-run execution

**Content Planner** — content structure only (pillars, funnel, ideas, sequence, channels). Requires Strategist + Researcher outputs. No post copy, assets, or scheduling.

```bash
uv run pytest tests/test_phase_ai_33_content_planner_specialist_execution.py -q
```

- `output_type: content_plan` with `content_pillars`, `post_ideas`, `dependencies_for_copywriter`, etc.
- Missing strategist → **409** `Content Planner requires completed Strategist output`
- Missing researcher → **409** `Content Planner requires completed Researcher output`

## Phase AI.34 — Copywriter specialist dry-run execution

**Copywriter** — draft post copy (`content_copy`) from Strategist + Researcher + Content Planner outputs. No `ContentAsset`, tools, or child `AgentRun`.

```bash
uv run pytest tests/test_phase_ai_34_copywriter_specialist_execution.py -q
```

- `structured_data.content_items[]` with `headline`, `hook`, `body`, `cta`, `funnel_stage`, `content_pillar`, `channel` (optional `source_post_idea`)
- Missing strategist / researcher / planner → **409** with exact dependency messages

## Phase AI.35 — Critic specialist dry-run execution

**Critic** — quality review (`critique`) after Strategist + Researcher + Content Planner + Copywriter. No auto approve/reject, no `ContentAsset` changes.

```bash
uv run pytest tests/test_phase_ai_35_critic_specialist_execution.py -q
```

- `structured_data`: `strengths`, `weaknesses`, `inconsistencies`, `missing_information`, `improvement_actions`, `approval_recommendation` (`approve` | `revise` | `reject`)
- Missing copywriter (or earlier specialist) → **409** with exact dependency messages

## Phase AI.36 — Analyst specialist dry-run execution

**Analyst** — execution feasibility (`analysis`) after the full five-specialist pipeline including Critic.

```bash
uv run pytest tests/test_phase_ai_36_analyst_specialist_execution.py -q
```

- `structured_data`: `risks`, `resource_requirements`, `channel_fit`, `funnel_gaps`, `execution_complexity`, `kpi_recommendations`
- Missing critic (or earlier specialist) → **409** with exact dependency messages
- Completes **MVP six** specialists on `execute-specialist`

## Phase AI.37–AI.38 — Pipeline validation + run completion

**AI.37** — `MarketingPipelineExecutionService` centralizes the dependency matrix, prior-output assembly, and exact **409** messages. `SpecialistExecutionService` delegates validation to it (no auto-run).

**AI.38** — After each successful `execute-specialist`, `complete_if_all_tasks_completed` marks the run `succeeded` when every task snapshot is `specialist_completed` (not placeholder/skipped/pending). `result_summary.mode` = `specialist_pipeline`.

```bash
uv run pytest tests/test_phase_ai_37_marketing_pipeline_validation.py tests/test_phase_ai_38_marketing_run_completion.py -q
```

API: `ExecuteMarketingSpecialistTaskResponse` adds `execution_run_status` and `run_completed`.

## Phase AI.39 — Marketing pipeline production freeze

**Freeze only** — no new features. Locks AI.27–AI.38 before **AI.40+** (`ContentAsset` branch).

```bash
uv run pytest tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

Audit: [docs/phase_ai_39_marketing_pipeline_readiness_audit.md](docs/phase_ai_39_marketing_pipeline_readiness_audit.md)

## AI.27–AI.39 Marketing Pipeline Layer

Production marketing **conveyor** (not LangGraph / swarm): one specialist, one manual `execute-specialist`, one `MarketingSpecialistOutput` per task.

```mermaid
flowchart LR
  Chat["Agent chat\nplanning only"] --> Save["Save MarketingPlan\ndraft"]
  Save --> Approve["Approve plan\nversion pin"]
  Approve --> Run["Execution run\nstart → running"]
  Run --> S["Strategist"]
  S --> R["Researcher"]
  R --> P["Content Planner"]
  P --> C["Copywriter"]
  C --> Cr["Critic"]
  Cr --> A["Analyst"]
  A --> Done["Run succeeded\nspecialist_pipeline"]
```

### Endpoint families

| Layer | Endpoints |
|-------|-----------|
| Chat | `POST /projects/{id}/agent-chat`, `.../block-actions` (`save_marketing_plan`) |
| Plans | `/marketing-plans`, `.../approve`, `.../archive` |
| Runs | `/marketing-plan-execution-runs`, `.../start`, `.../cancel` |
| Execute | `POST .../tasks/{task_index}/execute-specialist` |
| Outputs | `/marketing-specialist-outputs`, `.../approve`, `.../archive` |

### Safety boundaries (frozen)

- Approved plan version only for execution runs; `running` run required for execute.
- Dependency matrix in `MarketingPipelineExecutionService` (AI.37); first missing prior → **409**.
- Completion when **all** tasks `specialist_completed` only (AI.38) — not placeholder/skipped/pending.
- No `ContentAsset`, no child `AgentRun`, no tools, no raw provider payload on specialist path.
- Chat layer (AI.26) contracts unchanged for marketing work.

### Out of scope before AI.40+

ContentAsset conversion, publish/export, media generation, web research, MCP/tools, LangGraph marketing, auto-run full pipeline, parallel execution, billing/token accounting.

### Full regression (AI.27–AI.39)

```bash
uv run pytest \
  tests/test_phase_ai_27_marketing_orchestrator_skeleton.py \
  tests/test_phase_ai_28_marketing_plan_persistence.py \
  tests/test_phase_ai_29_marketing_plan_execution_skeleton.py \
  tests/test_phase_ai_30_marketing_specialist_output_skeleton.py \
  tests/test_phase_ai_31_strategist_specialist_execution.py \
  tests/test_phase_ai_32_researcher_specialist_execution.py \
  tests/test_phase_ai_33_content_planner_specialist_execution.py \
  tests/test_phase_ai_34_copywriter_specialist_execution.py \
  tests/test_phase_ai_35_critic_specialist_execution.py \
  tests/test_phase_ai_36_analyst_specialist_execution.py \
  tests/test_phase_ai_37_marketing_pipeline_validation.py \
  tests/test_phase_ai_38_marketing_run_completion.py \
  tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

Roadmap history: [docs/phase_ai_34_38_marketing_pipeline_roadmap.md](docs/phase_ai_34_38_marketing_pipeline_roadmap.md)

## Wave 3 — Content Production Layer (AI.40–AI.45, frozen)

Knowledge conveyor (AI.27–AI.39) is frozen. **Content production** (AI.40–AI.45) is frozen — explicit objects only, no publish.

```mermaid
flowchart LR
  Copy["Approved Copywriter output"] --> Asset["ContentAsset draft"]
  Asset --> Review["review workflow"]
  Review --> Appr["approved asset"]
  Appr --> PubPkg["PublicationPackage draft"]
```

| Phase | Intent |
|-------|--------|
| AI.40 | Explicit Copywriter → `ContentAsset` draft |
| AI.41 | Provenance columns on assets |
| AI.42 | `draft` → `review` → `approved` / `archived` |
| AI.43–AI.44 | `PublicationPackage` + explicit create |
| AI.45 | Production freeze |

Audit: [docs/phase_ai_45_content_production_readiness_audit.md](docs/phase_ai_45_content_production_readiness_audit.md) · Roadmap: [docs/phase_ai_40_45_content_production_layer_roadmap.md](docs/phase_ai_40_45_content_production_layer_roadmap.md)

```bash
uv run pytest \
  tests/test_phase_ai_40_copywriter_content_asset_conversion.py \
  tests/test_phase_ai_42_content_asset_review_workflow.py \
  tests/test_phase_ai_43_publication_package_foundation.py \
  tests/test_phase_ai_44_content_asset_publication_package_conversion.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py -q
```

**Next recommended:** AI.50+ Media Production Layer (not AI.60+ publishing).

## Wave 4 — Media Production Layer (AI.50–AI.55, frozen)

Approved content → **MediaBrief** (review workflow) → placeholder **MediaAsset**. **No generation** until AI.56–59.

Audit: [docs/phase_ai_55_media_production_readiness_audit.md](docs/phase_ai_55_media_production_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_50_media_brief_foundation.py \
  tests/test_phase_ai_51_content_asset_media_brief_conversion.py \
  tests/test_phase_ai_52_media_brief_review_workflow.py \
  tests/test_phase_ai_53_media_asset_foundation.py \
  tests/test_phase_ai_54_media_brief_media_asset_conversion.py \
  tests/test_phase_ai_55_media_production_freeze_invariants.py -q
```

**Next:** AI.56–59 generation providers — **not** AI.60+ publishing first.

## Wave 5 — Media Generation Layer (AI.56–AI.59, frozen)

Approved **MediaBrief** → **MediaGenerationJob** → **MediaAsset** (metadata/refs only). Mock by default; OpenAI Images gated.

Audit: [docs/phase_ai_59_media_generation_readiness_audit.md](docs/phase_ai_59_media_generation_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_56_media_generation_abstraction.py \
  tests/test_phase_ai_57_openai_images_provider_gated.py \
  tests/test_phase_ai_58_media_asset_storage_boundary.py \
  tests/test_phase_ai_59_media_generation_freeze_invariants.py -q
```

**Not in this wave:** Flux, Canva, HeyGen, video, publishing.

## Wave 6 — Publishing Foundation (AI.60–AI.65, frozen)

Approved **PublicationPackage** → **PublicationPackageJob** → dry-run only. No real Telegram/Instagram/LinkedIn send.

Audit: [docs/phase_ai_65_publishing_foundation_readiness_audit.md](docs/phase_ai_65_publishing_foundation_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_60_publishing_channel_registry.py \
  tests/test_phase_ai_61_publication_package_approval.py \
  tests/test_phase_ai_62_publication_job_skeleton.py \
  tests/test_phase_ai_63_dry_run_publisher.py \
  tests/test_phase_ai_64_publishing_observability.py \
  tests/test_phase_ai_65_publishing_foundation_freeze_invariants.py -q
```

**Next:** Real platform adapters + scheduling (post-freeze), only after operational review.

## Wave 6b — Publishing Reliability (AI.66–AI.69, frozen)

Idempotency, replay, `snapshot_hash` tamper detection. Still **dry-run only**.

Audit: [docs/phase_ai_69_publishing_reliability_readiness_audit.md](docs/phase_ai_69_publishing_reliability_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_66_publication_job_idempotency.py \
  tests/test_phase_ai_67_publication_job_replay.py \
  tests/test_phase_ai_68_payload_snapshot_integrity.py \
  tests/test_phase_ai_69_publishing_reliability_freeze_invariants.py -q
```

## Wave 7 — Telegram Publishing (AI.70–AI.75, frozen)

First **real** adapter (Telegram only), behind flags. Explicit `execute` — no scheduler.

Audit: [docs/phase_ai_75_telegram_publishing_readiness_audit.md](docs/phase_ai_75_telegram_publishing_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_70_publishing_provider_abstraction.py \
  tests/test_phase_ai_71_telegram_channel_secret_boundary.py \
  tests/test_phase_ai_72_telegram_provider_gated.py \
  tests/test_phase_ai_73_real_publish_endpoint.py \
  tests/test_phase_ai_74_telegram_publish_audit_metrics.py \
  tests/test_phase_ai_75_telegram_publishing_freeze_invariants.py -q
```

## Wave 8 — Publishing Scheduler (AI.76–AI.79, frozen)

Schedule **existing** queued `PublicationPackageJob` rows (approved package + active channel). Explicit due scan and dispatch — **no background worker**.

Audit: [docs/phase_ai_79_publishing_scheduler_readiness_audit.md](docs/phase_ai_79_publishing_scheduler_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_76_scheduled_publication_jobs.py \
  tests/test_phase_ai_77_publishing_schedule_service.py \
  tests/test_phase_ai_78_scheduler_audit_metrics.py \
  tests/test_phase_ai_79_publishing_scheduler_freeze_invariants.py -q
```

## Wave 9 — MVP E2E Demo (AI.80–AI.85, frozen)

One verifiable path from marketing plan through scheduled Telegram package job. No new platforms or agents.

Audit: [docs/phase_ai_85_mvp_demo_readiness_audit.md](docs/phase_ai_85_mvp_demo_readiness_audit.md)

```bash
uv run python scripts/seed_e2e_demo.py
# Optional v2 marketing outputs (offer → ad creative, mock LLM):
uv run python scripts/seed_e2e_demo.py --include-v2-marketing
uv run pytest \
  tests/test_phase_ai_80_e2e_demo_seed.py \
  tests/test_phase_ai_81_demo_flow_status.py \
  tests/test_phase_ai_83_content_production_provenance.py \
  tests/test_phase_ai_84_mvp_safety_regression.py -q
```

## Marketing department v2 (AI.110–AI.125, frozen at AI.119)

Baseline **14-role department** (frozen six + eight v2 executables). Frozen pipeline unchanged; v2 deps in separate matrix.

- Roadmap: [docs/phase_ai_110_marketing_department_v2_roadmap.md](docs/phase_ai_110_marketing_department_v2_roadmap.md)
- Freeze: [docs/phase_ai_119_marketing_department_v2_freeze.md](docs/phase_ai_119_marketing_department_v2_freeze.md)
- Readiness: [docs/phase_ai_125_marketing_department_v2_readiness_audit.md](docs/phase_ai_125_marketing_department_v2_readiness_audit.md)

```bash
uv run pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q
```

## Product Scenario Builder (AI.126–AI.135)

Business scenarios compose the 14-role department into draft marketing plans — users pick outcomes, not specialists.

- Roadmap: [docs/phase_ai_126_scenario_roadmap.md](docs/phase_ai_126_scenario_roadmap.md)
- Readiness: [docs/phase_ai_135_scenario_builder_readiness_audit.md](docs/phase_ai_135_scenario_builder_readiness_audit.md)

```bash
uv run pytest tests/test_phase_ai_134_scenario_builder_regression.py -q
uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen
```

## Scenario Auto-Run Wizard (AI.136–AI.145)

Manual campaign wizard: one **Advance** click = one safe pipeline step through dry-run job (no real publish).

- Roadmap: [docs/phase_ai_136_scenario_wizard_roadmap.md](docs/phase_ai_136_scenario_wizard_roadmap.md)
- Readiness: [docs/phase_ai_145_scenario_wizard_readiness_audit.md](docs/phase_ai_145_scenario_wizard_readiness_audit.md)

```bash
uv run pytest tests/test_phase_ai_144_scenario_wizard_regression.py -q
uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen
```

## Wave 10 — Beta Readiness (AI.86–AI.90, frozen)

Onboarding checklist, soft limits, normalized API errors, beta admin dashboard. No billing or scope expansion.

Audit: [docs/phase_ai_90_beta_readiness_audit.md](docs/phase_ai_90_beta_readiness_audit.md)

```bash
uv run pytest tests/test_phase_ai_90_beta_readiness_freeze.py -q
```

## Wave 11 — Beta QA loop (AI.91–AI.95, frozen)

Beta feedback reports, admin triage, demo failure markers, safe QA export. Diagnostic contour only — not a support CRM.

Audit: [docs/phase_ai_95_beta_qa_readiness_audit.md](docs/phase_ai_95_beta_qa_readiness_audit.md)

```bash
uv run pytest tests/test_phase_ai_95_beta_qa_readiness_freeze.py tests/test_phase_ai_90_beta_readiness_freeze.py -q
```

## Wave 12 — Beta Launch Pack (AI.96–AI.100, frozen)

Access gate, tester guide, demo reset, launch smoke — no new product features.

Audit: [docs/phase_ai_100_beta_launch_readiness_audit.md](docs/phase_ai_100_beta_launch_readiness_audit.md)

```bash
uv run alembic upgrade head
uv run python scripts/smoke_beta_launch.py
uv run pytest tests/test_phase_ai_100_beta_launch_freeze.py tests/test_phase_ai_95_beta_qa_readiness_freeze.py -q
```

## Roadmap — AI.40+ (after freeze)

**Fixed package** before implementation: [docs/phase_ai_34_38_marketing_pipeline_roadmap.md](docs/phase_ai_34_38_marketing_pipeline_roadmap.md)

| Wave | Phases | Intent |
|------|--------|--------|
| 1 | ~~AI.34–AI.36 MVP six specialists~~ | All execute via `MarketingSpecialistOutput` only |
| 2 | ~~AI.37–AI.39 freeze~~ | Validation + completion + production freeze |

**AI.40+** (new branch): approved Copywriter output → `ContentAsset` draft conversion — see [AI.27–AI.39 Marketing Pipeline Layer](#ai27ai39-marketing-pipeline-layer).

## AI.19–AI.26 Agent Chat Layer

Production-ready **specialist chat** (sessions, blocks, actions, history rebuild, search, observability). Phases AI.19–AI.25 implement behavior; **AI.26 freezes** invariants — no new product features on this layer until the next phase.

### Product model

| Path | Entrypoint | Behavior |
|------|------------|----------|
| Big / ambiguous task → **General** agent | `general_delegation` | `detect_general_domain` routes to marketing / programmer / media child runs |
| Small / specialist task → **Programmer / Media / Marketer** | `direct_specialist` | No General routing; scope gate for out-of-domain clarifications |

Supported domains: `unknown`, `marketing`, `programmer`, `media`.

### Safety boundaries

- Rolling session history (`AGENT_CHAT_SESSION_HISTORY_LIMIT`, default **10**) — not long-term memory
- History excludes tool logs, secrets, configs; metadata excludes full drafts / `output_payload`
- `blocks[]` on send and on GET messages (server rebuild from `source_run_id`)
- Block actions are server-authoritative; Programmer/Media drafts stay `persisted: false`
- Search: title/content only — not `message_metadata` or run `output_payload`
- Audit + metrics: counts and safe metadata only — no raw prompts or message bodies

### Endpoints (`/projects/{id}/agent-chat`, alias `/chat/...`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/agent-chat` | Send message |
| GET | `/agent-chat/sessions` | Session list (search, filters) |
| POST | `/agent-chat/sessions/{id}/archive` | Archive |
| GET | `/agent-chat/sessions/{id}/messages` | History + rebuilt `blocks` |
| POST | `/agent-chat/block-actions` | Copy / export / marketing persistence |
| GET | `/agent-chat/search-messages` | Message search |
| GET | `/agent-chat/metrics` | Operational counts |
| GET | `/agent-chat/audit-events` | Safe audit log |

UI: `/agents/chat` (session sidebar, blocks, observability panel).

### Out of scope (frozen)

Streaming, vector memory, summarization LTM, embeddings, billing/token accounting, media generation, Canva/Figma/HeyGen, programmer filesystem/GitHub/shell/deploy, marketer 12-subagent expansion, Langfuse/external telemetry, approve/schedule/publish from chat.

### Docs & regression

- Audit: [`docs/phase_ai_26_chat_production_readiness_audit.md`](docs/phase_ai_26_chat_production_readiness_audit.md)

```bash
uv run pytest \
  tests/test_phase_ai_19_chat_sessions.py \
  tests/test_phase_ai_20_chat_session_ux.py \
  tests/test_phase_ai_21_chat_message_blocks.py \
  tests/test_phase_ai_22_chat_block_actions.py \
  tests/test_phase_ai_23_history_block_rebuild.py \
  tests/test_phase_ai_24_chat_search.py \
  tests/test_phase_ai_25_chat_observability.py \
  tests/test_phase_ai_26_chat_freeze_invariants.py -q
```

## Phase AI.14.2 — Multi-subagent chain demo hardening

UI chain panel on `/agents/chat`, run details at `/agent-runs/{id}`, demo seed creates active marketer agents.

**Backend `.env` for interactive chain demo:**

```bash
AGENT_CHAT_TOOLS_ENABLED=true
TOOLS_PROVIDER_ENABLED=true
# Optional — plan draft / revision / generate assets in chat:
AGENT_WRITE_TOOLS_ENABLED=true
CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED=true
CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED=true
```

**Demo:** seed → AI Chat → campaign **Q2 Launch Demo** → orchestrator → `Запусти новый продукт в Telegram`

```bash
uv run python scripts/seed_demo_marketing_flow.py --refresh-api-key
uv run pytest tests/test_subagent_chain_execution.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
uv run pytest tests/test_phase_ai_14_2_chain_demo_smoke.py
```

See [docs/ui_demo_smoke_checklist.md](docs/ui_demo_smoke_checklist.md) step 15.

## Phase AI.7.1 — Agent chat revision readiness audit (freeze)

First **semantic content** agent in chat — freeze boundaries before AI.8 (campaign-aware copywriter).

- `docs/phase_ai_7_revision_readiness_audit.md`
- Draft revision: same asset id; approved source → new draft revision asset
- Structured `revised_assets`: `{ asset_id, version }` only (no full body)
- No chat approve / schedule / publish / publication jobs / archive

```bash
uv run pytest tests/test_agent_chat_revision_tool.py
uv run pytest tests/test_phase_ai_7_revision_invariants.py
```

Not in this freeze: AI.8 campaign-aware copywriter; chat approve/schedule/publish/archive.

## Phase 4.7 — Rollback as new draft revision

`POST .../content-assets/{id}/rollback-to-version` — новый **draft** из выбранной версии **approved** asset (clone-only, source не меняется). `metadata.rollback`, outbox `content_asset.rollback_revision_created`. Draft/archived source → 409.

## API

| Method | Path | Описание |
|--------|------|----------|
| GET | `/health` | App + PostgreSQL + Redis |
| GET | `/health/operations` | Schedulers, graph version, pending outbox / queue owners (no secrets) |
| GET | `/version` | Версия и окружение |
| GET | `/projects/{id}/operational-metrics` | 24h metrics: runs, handoff, outbox, webhooks, Redis depth |
| GET | `/me/operational-metrics` | Owner-wide operational metrics |
| POST | `/projects/{id}/events/replay-batch` | Batch-reset failed/dead_lettered outbox (no dispatch) |
| POST | `/agent-runs/handoff/replay-batch` | Batch re-queue handoff DLQ children |
| DELETE | `/projects/{id}/webhook-deliveries/cleanup` | Delete delivery logs older than N days (7–365) |
| POST | `/agent-runs/{id}/replay` | Clone failed/cancelled run → new queued run (no auto-execute) |
| POST | `/agent-runs/{id}/execute` | Production execute (atomic claim, optional `Idempotency-Key` header) |
| POST | `/agent-runs/{id}/execute-dry-run` | Debug: always classic |
| POST | `/agent-runs/{id}/execute-graph-dry-run` | Debug: always LangGraph |
| POST | `/webhooks/telegram` | Приём webhook (secret + PII sanitize) |
| CRUD | `/users` | Регистрация пользователя (без API key) |
| Auth | `/auth/api-keys` | Управление API keys |
| CRUD | `/projects`, `/tasks`, `/memory` | REST + ownership (Bearer API key) |
| CRUD | `/projects/{id}/marketing-briefs` | Marketing briefs (Phase 4.0) |
| CRUD | `/projects/{id}/content-assets` | Content assets (Phase 4.0) |
| CRUD | `/projects/{id}/publishing-channels` | Publishing destinations (Phase 6.0, HTTP-only) |
| CRUD | `/projects/{id}/publication-jobs` | Publication queue (Phase 6.0, approved assets only) |
| POST | `/projects/{id}/publication-jobs/process` | Manual publication worker drain (Phase 6.1) |
| POST | `/projects/{id}/publication-jobs/{id}/replay` | Re-queue failed/cancelled job (Phase 6.3) |
| POST | `/projects/{id}/publication-jobs/replay-batch` | Batch replay (Phase 6.3) |
| GET | `/projects/{id}/publication-deliveries` | Publication delivery attempt logs (Phase 6.1) |
| Registry | `/agents` | Agent registry (Bearer API key, без LLM) |
| Logging | `/agent-runs` | Agent run journal + dry-run executor (Bearer API key) |
| Logging | `/llm-requests` | LLM call journal (Bearer API key, без провайдера) |

Полная схема: `http://127.0.0.1:8000/docs`

## Структура

См. `docs/architecture.md` и `AGENTS.md`.

### General Business Operator (AI.176–AI.195)

Rule-based operator: пользователь описывает задачу → analyze → (clarify при низкой confidence) → preview → подтверждение → кампания → Action Center.  
Assist mode (AI.186–AI.195): порог confidence **0.65**, без LLM, без auto-create.  
LLM fallback (AI.196–AI.205): только при низкой rule-confidence, `BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED=false` по умолчанию.  
Campaign Brief Intake (AI.206–AI.215): analyze → brief complete → confirm → create с `brief_id`; порог completeness **100**.  
Marketing Data Tools v1 (AI.216–AI.225): Wordstat / Metrica / image mock tools — `POST .../marketing-tools/{tool_type}/calls`, без auto-call.  
Marketing Skills v1 (AI.226–AI.235): skill runs поверх tools — `POST .../marketing-skills/{skill_type}/runs`, data skills → tool только при `create_tool_call=true`.  
Regression: `uv run pytest tests/test_phase_ai_184_business_operator_regression.py tests/test_phase_ai_194_business_operator_assist_regression.py tests/test_phase_ai_204_business_operator_llm_fallback_regression.py tests/test_phase_ai_214_campaign_brief_intake_regression.py tests/test_phase_ai_224_marketing_data_tools_regression.py tests/test_phase_ai_235_marketing_skills_freeze.py -q`

## Контракты данных

Все сущности: `app/schemas/contracts.py` (`User`, `Project`, `Agent`, `Task`, `MemoryItem`, `LLMRequest`, `LLMResponse`, `MarketingBrief`, `ContentAsset`).

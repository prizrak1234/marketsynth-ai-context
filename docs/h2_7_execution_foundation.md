# H2.7 — Specialist Execution Foundation (slice 1)

Status: **completed locally** (content.telegram_post draft path only).

## Baseline checkpoint

| Field | Value |
| --- | --- |
| Branch | `master` |
| Checkpoint commit | `eaca68c` (H2.6A/H2.6A-R before H2.7) |
| Alembic head | `20260716_0046` |
| Active database | `botfazer_cph1` (PostgreSQL) |
| Feature flag | `CONTENT_DRAFT_EXECUTION_ENABLED` (default `false`) |
| Default draft LLM | `CONTENT_DRAFT_LLM_PROVIDER=mock` |

## Scope of this slice

Governed chain for the first text skill:

```
UserRequest
→ content.telegram_post
→ approved Knowledge Snapshot
→ PromptPackage (assembler)
→ Tool Profile (no tools)
→ one LLM call
→ Quality Gate
→ ContentDraftResult (persisted)
→ Specialist Activity card + owner review
```

## Explicitly NOT in this slice

- programmer / research / strategy execution
- Make / n8n execution
- Pinecone retrieval
- Yandex Direct write
- publication / Campaign / budget actions
- Firecrawl / XMLRiver research skill execution (adapters only)
- second Runtime / Agent Registry / Task engine
- changes to the approved Home page layout (card is additive)

## Deliverables

### 1. Integration Registry

`app/integrations/registry.py`

- Authoritative `IntegrationDefinition` list.
- Credential presence ≠ readiness.
- Current classification:
  - OpenAI / OpenRouter / GPTunnel → ready when key present
  - Firecrawl / XMLRiver → configured (read-only adapters)
  - Make → configured, execution disabled
  - n8n → **blocked** (SSL mismatch + HTTP 405)
  - Pinecone → **disabled** by policy
  - Yandex Direct / Metrica → configured, write disabled

### 2. BusinessTool abstraction

`app/business_tools/`

- Normalized tools: `knowledge_retrieval`, `web_search`, `source_fetch`, …
- Skills never reference `FIRECRAWL_API_KEY` / `MAKE_API_KEY`.
- `WORKFLOW_AUTOMATION` and `ADVERTISING_PLATFORM` are not resolvable.

### 3. Tool Profiles

`app/specialist_skills/tool_profiles.py`

- Per-role allow / deny lists.
- Global hard denies: Make/n8n workflows and advertising platform for every role.
- `content_specialist` for this slice: knowledge retrieval only, max_calls=0.

### 4. PromptPackage + Assembler

- Contracts in `app/schemas/contracts.py`
- Assembler: `app/prompts/specialist/assembler.py`
- Constitutional: `app/prompts/specialist/constitutional.py`
- Roles: `app/prompts/specialist/roles.py`
- Skill instruction: `app/prompts/specialist/skills.py`

Assembly order: constitutional → role → skill → knowledge → user request →
output schema → quality gates → tool policy → locale.

### 5. content.telegram_post draft execution

`app/services/content_draft_service.py`

- Flag-gated (`CONTENT_DRAFT_EXECUTION_ENABLED`)
- Mandatory knowledge snapshot
- One LLM call via existing adapter (`mock` / `openai` / `openrouter`)
- No tools, no publication
- Result + PromptPackage hash persisted on `user_requests`
- Review API: `POST /user-requests/{id}/content-draft/review`

### 6. OpenRouter

- `LLMProvider.OPENROUTER` added
- Routed through `LiteLLMAdapter` + `get_llm_adapter`
- No secret in prompt / UI / DB

### 7. Firecrawl / XMLRiver

- Read-only adapters under `app/business_tools/providers/`
- Return Source **candidates** only (`is_evidence=False`)
- Not wired to an executable research skill in this slice

### 8. Specialist Activity card

`web/src/components/workspace/home/specialist-activity-card.tsx`

User-facing labels:

- Специалист / Экспертиза / Использованные материалы / Статус
- Actions: Принять / Изменить / Создать вариант / Скопировать / Отклонить
- No publish button
- Diagnostics (provider/model/prompt hash) only for owner/admin

### 9. Tests

`tests/test_phase_h2_7_specialist_execution.py` — 12 passed.

Covered: registry governance, hard denies, OpenRouter wiring, prompt assembly,
draft generation (mock), refresh persistence, review, clarification without draft,
invalid publish action rejected.

## Manual acceptance (owner)

1. Set in `.env`:

```
CONTENT_DRAFT_EXECUTION_ENABLED=true
CONTENT_DRAFT_LLM_PROVIDER=mock
```

(or `openai` / `openrouter` with the corresponding model allowlist)

2. Restart API.

3. On Home, send a fully-specified Telegram post request (topic, audience,
   objective, tone, length, CTA) or pass `skill_inputs`.

4. Expect: Specialist Activity card with expertise labels, draft body, no publish.

## Owner acceptance fix (post slice-1 review)

Functional acceptance initially failed because:

1. CTA phrase «В конце задай вопрос» was not inferred → blocked on missing `CTA`.
2. Absent `length` was hard-required → blocked generation.
3. User-facing copy leaked route/skill/snapshot jargon.

Fix (no new skill):

- Hard required only: `topic`, `audience`, `objective`.
- Soft defaults: `length=standard` (700–1200), tone, factuality; CTA semantic inference (`discussion_question`, …).
- Natural acknowledgement without technical codes.
- Runtime for acceptance: `CONTENT_DRAFT_EXECUTION_ENABLED=true`, `CONTENT_DRAFT_LLM_PROVIDER=openai`, `CONTENT_DRAFT_LLM_MODEL=gpt-4o-mini` (requires `uv sync --extra llm` for LiteLLM).

Regression: `uv run pytest tests/test_phase_h2_7_specialist_execution.py -q` (15 tests).

## Confirmations

- No unrestricted external execution.
- No publication, Campaign or budget action.
- No remote Git operations.
- n8n remains blocked; TLS verification was not bypassed.
- Pinecone remains disabled.
- No parallel Runtime created.

---

Marketsynth Specialist Execution Foundation (slice 1) completed locally.
Specialists now use versioned prompt packages, approved knowledge snapshots
and explicit tool profiles.
Connected integrations are exposed only through normalized, permissioned
business tools.
Draft-only specialist results show the expertise and materials actually used.
Make, n8n, advertising writes, publication and budget execution remain behind
explicit approval boundaries.
No parallel Runtime or unrestricted external execution was created.
No remote Git operations were performed.
Ready for owner review of the first text skill (`content.telegram_post`).

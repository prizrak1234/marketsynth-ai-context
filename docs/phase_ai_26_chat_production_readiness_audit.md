# Phase AI.26 — Agent chat production readiness audit (freeze)

**Status:** Production-ready freeze for the agent chat layer (AI.19–AI.25).  
**Not ready for:** streaming, vector memory, billing, media generation, external telemetry, or marketer orchestrator expansion without a new phase.

This document freezes what BotFazer guarantees for **specialist chat** after phases AI.19–AI.26. It is the reference for regressions and for what may be built next (e.g. marketing orchestrator expansion, media generation tools) only **after** this freeze.

Related tests:

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

---

## Executive summary

| Area | Verdict |
|------|---------|
| Session-scoped chat (AI.19) | Yes — rolling history, not LTM |
| Frontend-safe blocks (AI.21) | Yes — `blocks[]` on send + history rebuild |
| Block artifact actions (AI.22) | Yes — server-authoritative; marketing persistence only |
| History block rebuild (AI.23) | Yes — GET messages returns rebuilt `blocks` |
| Search (AI.24) | Yes — SQL LIKE on title/content only |
| Observability (AI.25) | Yes — safe audit events + metrics counts |
| Programmer/Media persistence | **No** — consultation-only drafts/briefs |
| Streaming / embeddings / billing | **No** |

---

## Product model

| User path | Entrypoint | Behavior |
|-----------|------------|----------|
| Big / ambiguous task → General agent | `general_delegation` | `detect_general_domain` routes to marketing / programmer / media child runs (depth ≤ 2) |
| Small / specialist task → Programmer / Media / Marketer agent | `direct_specialist` | No General routing; scope gate via same domain detector for out-of-scope clarifications |

Supported **domains** (session + execution metadata):

| Domain | Meaning |
|--------|---------|
| `unknown` | General / undecided |
| `marketing` | Campaigns, content, launches |
| `programmer` | Technical consultation (non-persistent) |
| `media` | Visual brief consultation (non-persistent) |

---

## Session model (AI.19–AI.20)

- Table: `agent_chat_sessions` — `owner_id`, `project_id`, `agent_id`, `entrypoint`, `domain`, `status`, `title`
- Status: `active` (default list filter) | `archived` (explicit filter only)
- Messages: `agent_chat_messages` — `role`, `content`, `message_metadata`, optional `agent_run_id`
- **Not** long-term memory: no chat content in `memory_items` or prompt LTM from chat history beyond the rolling window

### History boundary (AI.19)

- Config: `AGENT_CHAT_SESSION_HISTORY_LIMIT` (default **10**, max 50)
- Run input receives recent user/assistant turns only: `role` + `content`
- Excludes: system messages, tool logs, secrets, configs, full draft payloads in metadata

---

## Blocks contract (AI.21)

Assistant responses expose `blocks[]` (`ChatAssistantMessageBlock`):

| Block type | Typical domain |
|------------|----------------|
| `text` | Any |
| `clarification` | Scope / guidance |
| `draft` | Programmer technical task, marketing content plan |
| `brief` | Media visual brief, marketing brief |
| `error` | Safe user-facing errors only |

- Readable `assistant_message.content` is a summary — not a raw JSON dump of `output_payload`
- `message_metadata` stores `block_types`, `domain`, `execution_metadata`, `source_run_id` — **not** full drafts or `output_payload`

---

## Block actions (AI.22)

Server-computed `actions[]` per block. Client may only **request**; server rebuilds block from `source_run_id` + stored run output.

| Action | Marketing | Programmer / Media |
|--------|-----------|-------------------|
| `create_marketing_asset` | When data allows | Disabled |
| `create_marketing_brief` | When data allows | Disabled |
| `create_revision_from_approved` | When approved source id present | Disabled |
| `copy_text` / `export_markdown` | Yes | Yes |

Endpoint: `POST /projects/{id}/agent-chat/block-actions`

---

## History rebuild (AI.23)

`GET /projects/{id}/agent-chat/sessions/{session_id}/messages`

- Each message includes `blocks[]` (empty for user/system)
- Assistant blocks rebuilt from `message_metadata.source_run_id` → `AgentRun.output_payload`
- Missing/deleted run → text fallback block with copy/export only
- Default `limit=50`, max `100`, order ASC by `created_at`

---

## Search (AI.24)

`GET .../agent-chat/sessions` — optional `query` (min 2 chars) searches **title** and **message content** only.

`GET .../agent-chat/search-messages` — required `query`; searches **content** column only (not `message_metadata`, not `output_payload`).

Limits: sessions list default 50 / max 100; message search default 20 / max 50.

---

## Observability / audit (AI.25)

Table: `chat_audit_events` — safe operational visibility only.

| Event family | Examples |
|--------------|----------|
| Session | `chat.session.created`, `chat.session.archived` |
| Messages | `chat.message.user_appended`, `chat.message.assistant_appended` |
| Runs | `chat.run.started`, `chat.run.succeeded`, `chat.run.failed` |
| Block actions | `chat.block_action.requested`, `.succeeded`, `.failed` |
| Search | `chat.search.sessions`, `chat.search.messages` |

**Allowed in `safe_metadata`:** ids, counts, `content_length`, `query_length`, `block_types`, `action_type`, `latency_ms`, `error_code`, `safe_message`.

**Forbidden:** raw user/assistant text, queries, drafts, `output_payload`, prompts, tool results, provider responses, secrets.

Endpoints:

- `GET .../agent-chat/metrics` — aggregate counts only
- `GET .../agent-chat/audit-events` — default limit 50, max 200, `created_at DESC`

---

## HTTP API surface (chat)

Alias prefix: `/projects/{id}/chat/...` mirrors `/agent-chat/...` where noted.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/agent-chat` | Send message; returns session, messages, `blocks`, `output`, `execution_metadata` |
| GET | `/agent-chat/sessions` | UX list (preview, counts, filters, search) |
| POST | `/agent-chat/sessions/{id}/archive` | Archive session |
| GET | `/agent-chat/sessions/{id}/messages` | History with rebuilt `blocks` |
| POST | `/agent-chat/block-actions` | Execute block action (server-validated) |
| GET | `/agent-chat/search-messages` | Message search hits (preview only) |
| GET | `/agent-chat/metrics` | Operational counts |
| GET | `/agent-chat/audit-events` | Safe audit log |

---

## Safety boundaries (frozen)

1. **Programmer / Media** — `technical_task_draft` / `visual_brief` with `persisted: false`; empty tool allowlists; runs cannot spawn children.
2. **Direct specialist** — does not use General delegation path (`general_delegation` absent on direct sends).
3. **General** — still uses `detect_general_domain` for routing; marketing delegation unchanged from AI.15+.
4. **Chat history** — short rolling context only; `assert_history_safe_for_prompt` guards forbidden keys.
5. **Block actions** — server rebuilds from stored run; forged persistence on consultation blocks → 409.
6. **Search** — no metadata / output_payload inspection.
7. **Audit** — no message body duplication in logs.

---

## Explicit out of scope (do not add without new phase)

- Streaming responses / SSE
- Vector search, embeddings, semantic retrieval into prompts
- Summarization memory or chat → LTM promotion
- Billing, token accounting, cost attribution
- Image/video generation; Canva / Figma / HeyGen
- Programmer filesystem / GitHub / shell / deploy tools
- Marketer 12-subagent expansion in chat
- Langfuse / external APM wiring
- Approving assets, scheduling, publishing from chat
- Client-trusted block data for persistence
- Full draft bodies in `message_metadata` or audit `safe_metadata`

---

## Phase map (reference)

| Phase | Topic |
|-------|--------|
| AI.18 | Direct specialist chat |
| AI.19 | Sessions + history boundary |
| AI.20 | Session title, preview, list UX |
| AI.21 | Frontend-safe `blocks[]` |
| AI.22 | Block artifact actions |
| AI.23 | History block rebuild |
| AI.24 | Search + session filters |
| AI.25 | Observability + audit metrics |
| AI.26 | **This freeze** — invariants + docs |

---

## UI

- Route: `/agents/chat` (Next.js)
- Session sidebar: search, domain/status filters, message search, observability panel (metrics + recent audit)
- Live send uses `blocks` from POST response; history uses GET messages `blocks`

---

## Config defaults (frozen)

| Setting / endpoint | Default | Max |
|--------------------|---------|-----|
| `AGENT_CHAT_SESSION_HISTORY_LIMIT` | 10 | 50 (config field) |
| GET messages `limit` | 50 | 100 |
| GET sessions `limit` | 50 | 100 |
| GET search-messages `limit` | 20 | 50 |
| GET audit-events `limit` | 50 | 200 |

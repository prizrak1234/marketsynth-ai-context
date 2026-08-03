# Cursor Operating Rules

Rules for AI assistants working in the BotFazer repository. These apply to every session unless the user explicitly overrides them for a scoped task.

## 1. Preserve the product goal

**BotFazer replaces a marketing agency** — business operating system for marketing, not a chatbot or agent builder.

Before proposing architecture or UX, ask: *Does this help a business user reach a campaign outcome without manual tool orchestration?*

## 2. Do not reduce to chatbot

Forbidden framing:

- "Just add a chat endpoint that calls GPT."
- "Let the user pick agents from a marketplace."
- "Import all n8n workflows and run them."

Required framing:

- Business Operator → Campaign → Brief → Skills → Tools → Workflow → Content → Media → Publishing.
- Explicit actions, approvals, and read-only supervisor/workflow recommendations.

## 3. Do not bypass approval gates

Frozen layers require human confirmation for:

- Brief confirm before campaign create
- Plan / copywriter / asset / media brief / package / job approvals
- Publishing and schedule dispatch

Never auto-approve, auto-publish, or auto-schedule unless an explicit phase spec allows it.

## 4. Do not auto-run execution

Unless the active phase explicitly says otherwise:

| Layer | Default |
|-------|---------|
| Tools | Explicit API / action only |
| Skills | One skill per explicit run |
| Workflows | Checklist only — no step execution |
| Wizard | One `advance` at a time |
| Publishing | Human HTTP actions only |
| Background workers | Not allowed in foundation phases |

## 5. Respect frozen layers

Phases marked **frozen** in `AGENTS.md` and `docs/phase_ai_*_readiness_audit.md` must not be rewritten for convenience.

Extend via new contracts, new endpoints, or new registries — do not rip out frozen invariants.

## 6. Extend via contracts

New entities:

1. `app/schemas/contracts.py`
2. DB model + migration
3. Repository / service
4. Thin API route
5. Tests under `tests/`

Read `docs/DEVELOPMENT.md` before new features.

## 7. Secrets and safety

- All secrets via `app/core/config.py` and `.env` — **never** hardcode.
- **Never** put secrets in DB, metadata, logs, prompts, or docs.
- Inbound text → `sanitize_payload` before processing or logging.
- **Raw provider payloads forbidden** in API responses, campaign metadata, and skill context.
- Use **safe summaries** only (see `CampaignSkillContextService`).

## 8. Knowledge import vs product

- `knowledge/`, `skills/`, `workflows/raw/`, `standards/` are **reference corpus**.
- Import phases do **not** modify `app/`, migrations, or tests.
- Converting corpus → product requires a numbered phase with contracts and regression tests.

## 9. LangGraph and marketing pipeline

Do **not** add LangGraph, agent executors, or marketing pipeline orchestration unless the user explicitly requests a phase that allows it.

## 10. Tests and commits

- Every new endpoint needs tests in `tests/`.
- Do not commit unless the user asks.
- Do not skip hooks or force-push to main.

## Quick checklist before opening a PR

- [ ] Contracts first?
- [ ] No auto-run side effects?
- [ ] Sanitized / safe summaries only?
- [ ] Frozen layers intact?
- [ ] Moves agency-replacement goal forward?

## Related docs

- [PROJECT_VISION.md](PROJECT_VISION.md)
- [AGENT_OS_ARCHITECTURE.md](AGENT_OS_ARCHITECTURE.md)
- [AGENTS.md](../AGENTS.md)

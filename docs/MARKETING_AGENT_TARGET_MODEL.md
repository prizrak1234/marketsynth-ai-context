# Marketing Agent — Target Model

Target behavior derived from the Make prototype and agency operating practice. This is the **product north star** for the marketing agent layer — not necessarily fully implemented in every phase.

## Input channels

The marketing agent must accept business context from:

| Channel | Expectation |
|---------|-------------|
| **Text** | Goals, offers, audience descriptions, constraints |
| **Telegram** | Same semantics as text; webhook ingress with sanitization |
| **Voice** | Transcribed to text before processing (future) |
| **Photo** | Visual context for reports/creatives when relevant (future) |

All inbound content passes through `sanitize_payload` before logging or persistence.

## Output orientation

**Business-oriented, not tool-oriented.**

Bad: "Wordstat returned 400 rows."
Good: "Demand for implant keywords is moderate; prioritize hygiene packages for faster CPL."

## Data sources (when justified)

| Tool | Business question |
|------|-------------------|
| **Wordstat** | Is there search demand? Which themes? |
| **Yandex Metrica** | What happens on site? Traffic quality, goals, bottlenecks |
| **Image generation** | Visual reports, creatives, dashboard-style summaries when they aid decisions |

Use each tool **only when** the business question requires it.

## Required response format

Every substantive marketing agent response should follow:

### 1. Business conclusion

One clear answer: what this means for the client's goal (leads, revenue, launch readiness).

### 2. Key data

Only data that supports the conclusion — safe summaries, not raw provider payloads.

### 3. Prioritized recommendations

Each recommendation includes:

| Field | Description |
|-------|-------------|
| **Action** | What to do next (skill, campaign action, brief field) |
| **Effect** | Expected business impact |
| **Cost** | Time, budget, or complexity (qualitative OK in v1) |
| **Priority** | Order relative to other recommendations |

## Hard rules

1. **Never invent data** — if Wordstat/Metrica did not run, do not fabricate metrics.
2. **Never use tools just because they exist** — no "let me also pull Metrica" without a business reason.
3. **Never expose raw provider payloads** — use safe summaries in API, metadata, and UI.
4. **Never auto-run** skills, tools, workflows, or publishing unless the active phase explicitly allows it.
5. **Never bypass approval gates** — content, media, packages, jobs require human confirm where frozen layers say so.

## Mapping to BotFazer components

| Target behavior | Implementation path |
|-----------------|----------------------|
| Business conclusion + recommendations | Skill outputs, supervisor report, Control Center `next_action` |
| Wordstat / Metrica | `MarketingToolType` + skills `wordstat_research`, `metrica_analysis` |
| Visual reports | `visual_report` skill + image tool when enabled |
| Prioritized next steps | Skill suggestions, workflow suggestions, Action Center |
| Quality gate | Campaign Supervisor (read-only) |

## Anti-patterns

- Chatbot that only rewrites copy without campaign state.
- Tool dashboard with no brief or success metric.
- Auto-imported n8n workflow execution.
- LLM hallucinating competitor or traffic numbers.

## Related docs

- [PROJECT_VISION.md](PROJECT_VISION.md)
- [MARKETING_FRAMEWORKS_CONTEXT.md](MARKETING_FRAMEWORKS_CONTEXT.md)
- [CURSOR_OPERATING_RULES.md](CURSOR_OPERATING_RULES.md)

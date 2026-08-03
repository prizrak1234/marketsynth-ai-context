# Phase AI.225 — Marketing Data Tools Readiness Audit

**Date:** 2026-06-03  
**Scope:** Mock/read-only marketing data tool layer (AI.216–AI.224).

---

## 1. Product intent

Campaign Brief Intake closes input quality. **Marketing Data Tools v1** adds Make-style marketer capabilities: Wordstat (demand), Metrica (site behavior), image generation (creative) — via explicit tool calls, not agent auto-execution.

---

## 2. Principles (AI.216)

| Rule | Status |
|------|--------|
| Mock provider only | ✓ |
| No external API calls | ✓ |
| Explicit execution via API | ✓ |
| No agent auto-call | ✓ |
| Permission gates | ✓ |
| No secrets in input | ✓ |
| Safe audit logging | ✓ |

---

## 3. Contracts (AI.217)

`MarketingToolType` — wordstat, metrica, image_generation.

`MarketingToolCall` — id, owner_id, project_id, tool_type, input/output payloads, status, safe_metadata, error, timestamps.

`MarketingToolSuggestion` — read-only recommendations on operator / control center.

---

## 4. Tool skeletons

| Tool | Service | KB |
|------|---------|-----|
| Wordstat | `MarketingWordstatService` | `yandex_regions.py` |
| Metrica | `MarketingMetricaService` | `metrica_dimensions.py` + NL parser |
| Image | `MarketingImageGenerationService` | mock:// refs, max 1 image |

---

## 5. Registry + permissions (AI.221)

- `MarketingToolRegistry` — wordstat, metrica, image_generation handlers
- `MARKETING_DATA_TOOLS_ENABLED=false` by default (production)
- `MARKETING_DATA_TOOLS_MOCK_ENABLED=true` — dev auto-enable when `APP_ENV=development`
- Forbidden input keys rejected via existing tool security helpers
- Audit: `marketing_tool_call_audit` structlog event

---

## 6. Recommendations (AI.222)

Business Operator analyze/clarify and Campaign Control Center expose `tool_suggestions` — labels only, no execution.

---

## 7. API (AI.223)

```
POST /projects/{id}/marketing-tools/{tool_type}/calls
GET  /projects/{id}/marketing-tools/calls
GET  /projects/{id}/marketing-tools/calls/{call_id}
```

---

## 8. Configuration

```env
MARKETING_DATA_TOOLS_ENABLED=false
MARKETING_DATA_TOOLS_MOCK_ENABLED=true
```

---

## 9. Regression (AI.224)

```bash
uv run pytest tests/test_phase_ai_224_marketing_data_tools_regression.py -q
```

---

## 10. Known limits

- No real XMLRiver / Yandex Metrica / OpenAI image providers yet.
- Metrica NL parser is rule-based mock enrichment only.
- Tool suggestions do not track whether user already ran a tool.

---

## 11. Verdict

**Ready** for wiring real providers behind the same contracts and permission gates in a later phase.

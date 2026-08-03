# Phase AI.216 — Marketing Data Tools Roadmap

**Date:** 2026-06-03  
**Goal:** Bring Make-style marketer tooling into the Python contour — mock/read-only first.

---

## Tool roles

| Tool | Role |
|------|------|
| Wordstat | Demand / market research |
| Metrica | Site behavior / effectiveness |
| Image generation | Creative visualization |

---

## Principles

| Rule | Detail |
|------|--------|
| No agent auto-call | Explicit API execution only |
| Mock provider v1 | No external XMLRiver / Yandex / OpenAI calls |
| Permission gates | Disabled by default in production |
| No secrets in input | Forbidden keys rejected |
| Safe audit | Every call logged without PII/secrets |

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.216 | This roadmap |
| AI.217 | `MarketingToolCall` contracts |
| AI.218 | Wordstat mock skeleton |
| AI.219 | Metrica mock skeleton |
| AI.220 | Image generation mock skeleton |
| AI.221 | Registry + permissions |
| AI.222 | Operator / control center suggestions (read-only) |
| AI.223 | Tool call API |
| AI.224 | Regression |
| AI.225 | Freeze audit |

---

## API

```
POST /projects/{id}/marketing-tools/{tool_type}/calls
GET  /projects/{id}/marketing-tools/calls
GET  /projects/{id}/marketing-tools/calls/{call_id}
```

---

## Regression

```bash
uv run pytest tests/test_phase_ai_224_marketing_data_tools_regression.py -q
```

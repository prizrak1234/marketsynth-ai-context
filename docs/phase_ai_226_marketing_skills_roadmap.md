# Phase AI.226 — Marketing Skills Roadmap

**Date:** 2026-06-03  
**Goal:** Professional marketer processes on top of data tools — mock/rule-based v1.

---

## Skill vs Tool

| Layer | Role |
|-------|------|
| **Tool** | Hands — Wordstat, Metrica, image generation |
| **Skill** | Process — instruction + inputs + steps + optional tools + output schema |

---

## Principles

| Rule | Detail |
|------|--------|
| Explicit run only | `POST .../marketing-skills/{skill_type}/runs` |
| No agent auto-run | Skills recommend, user executes |
| Mock/rule-based v1 | No LLM generation in skill outputs |
| Data skills may call mock tools | Only when `create_tool_call=true` in input |
| Safe audit | Every run logged without secrets |

---

## Skills v1

| Skill | Purpose |
|-------|---------|
| segment_research | Segment profile + research questions |
| meaning_unpacking | Desires, benefits, fears, promises |
| offer_packaging | Strong offer structure |
| offer_justification | Business case + CTA |
| wordstat_research | Demand check via Wordstat tool |
| metrica_analysis | Traffic/behavior via Metrica tool |
| visual_report | Creative summary report |

---

## Deliverables

AI.226–AI.235 — contracts, registry, executors, API, control center UI, freeze.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q
```

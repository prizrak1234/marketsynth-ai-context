# Phase AI.235 — Marketing Skills Layer Readiness Audit

**Date:** 2026-06-03  
**Scope:** Professional marketer skill processes on mock tools (AI.226–AI.234).

---

## 1. Product intent

Tools are **hands** (Wordstat, Metrica, image). Skills are **processes** — when to research, how to unpack meaning, how to package/justify an offer, and how to turn data into business conclusions.

---

## 2. Skill vs Tool (AI.226)

| Layer | Role |
|-------|------|
| Tool | Atomic capability with safe I/O |
| Skill | Instruction + inputs + process + optional tools + output schema |

---

## 3. Contracts (AI.227)

`MarketingSkillType` — 7 skills including data skills `wordstat_research`, `metrica_analysis`.

`MarketingSkillRun` — persisted run with `used_tool_call_ids`, safe metadata, explicit status lifecycle.

---

## 4. Registry (AI.228)

`app/marketing/skills/registry.py` — name, purpose, required_inputs, optional_tools, output_type, out_of_scope per skill.

---

## 5. Qualitative skills (AI.229–AI.232)

Rule-based mock outputs aligned with agency worksheets:

- segment_research → soc_dem, pains, desires, research_questions
- meaning_unpacking → desires_table, benefit_mapping, promise_formulations
- offer_packaging → measurable_result, mechanism, offer_variants
- offer_justification → target_fit, value_breakdown, final_cta

---

## 6. Data skills (AI.233)

- `wordstat_research` / `metrica_analysis` attach mock tool output only when `create_tool_call=true`
- No agent auto-call; skill run is explicit via API

---

## 7. API + UI (AI.234)

```
POST /projects/{id}/marketing-skills/{skill_type}/runs
GET  /projects/{id}/marketing-skills/runs
GET  /projects/{id}/marketing-skills/runs/{run_id}
GET  /projects/{id}/marketing-skills/definitions
```

Campaign Control Center: `skill_suggestions` + Marketing Skills panel (run + output card).

---

## 8. Configuration

```env
MARKETING_SKILLS_ENABLED=false
MARKETING_SKILLS_MOCK_ENABLED=true
```

---

## 9. Regression

```bash
uv run pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q
```

---

## 10. Verdict

**Ready** — skill layer separates professional process from tools; real providers can plug into data skills later without redesign.

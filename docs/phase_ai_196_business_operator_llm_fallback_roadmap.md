# Phase AI.196 — LLM Business Operator Fallback Roadmap

**Date:** 2026-06-03  
**Goal:** Optional LLM intent classification when rule-based confidence is low — without replacing the rule-based primary path.

---

## Principles

| Rule | Detail |
|------|--------|
| Rule-based primary | LLM never runs when rule confidence ≥ threshold |
| LLM only when uncertain | `confidence < BUSINESS_OPERATOR_CONFIDENCE_THRESHOLD` |
| No auto-create | Campaign still requires explicit user confirm |
| Schema validation | LLM output must parse as `BusinessOperatorLLMIntent` |
| Invalid LLM → clarification | Fall back to assist clarifications |
| Off by default | `BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED=false` |

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.196 | This roadmap |
| AI.197 | `BusinessOperatorLLMIntent` contract |
| AI.198 | `app/prompts/business_operator.py` |
| AI.199 | `BusinessOperatorLLMService` |
| AI.200 | Merge rule + LLM in operator service |
| AI.201 | Safe audit extensions |
| AI.202 | `source`, confidence_before/after in API + UI |
| AI.203 | Feature flags |
| AI.204 | Regression |
| AI.205 | Freeze audit + docs |

---

## Merge logic (AI.200)

```
rule confidence >= threshold → rule_based (no LLM)

rule confidence < threshold:
  if LLM fallback disabled → clarification
  else call LLM:
    invalid schema/scenario → clarification
    LLM confidence > rule AND >= min_accept AND valid scenario → llm_fallback
    else → clarification
```

---

## Safety (AI.201)

Audit logs: `llm_used`, provider, model, confidence_before/after, selected_scenario.  
Forbidden in logs: raw prompt, raw completion, provider payload, secrets.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q
```

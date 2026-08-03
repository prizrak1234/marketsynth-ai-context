# Phase AI.205 — Business Operator LLM Fallback Readiness Audit

**Date:** 2026-06-03  
**Scope:** Optional LLM intent fallback when rule-based confidence is low (AI.196–AI.204).

---

## 1. Product intent

Rule-based Business Operator (AI.176–AI.195) handles clear requests. **LLM fallback** improves vague requests only when enabled — LLM is not the primary path and never auto-creates campaigns.

---

## 2. Principles (AI.196)

| Rule | Status |
|------|--------|
| Rule-based primary | ✓ |
| LLM only when confidence < threshold | ✓ |
| No campaign auto-create | ✓ |
| Schema validation on LLM output | ✓ |
| Invalid LLM → clarification | ✓ |
| Off by default | ✓ |

---

## 3. Contracts (AI.197)

`BusinessOperatorLLMIntent` — goal, industry, business_type, campaign_type, suggested_scenario, confidence, reasoning_summary, missing_fields.

`BusinessOperatorIntentSource` — `rule_based`, `llm_fallback`, `clarification`.

---

## 4. Implementation

| Component | Path |
|-----------|------|
| Prompts | `app/prompts/business_operator.py` |
| LLM service | `app/services/business_operator_llm_service.py` |
| Merge logic | `app/domain/business_operator_llm_merge.py` |
| Orchestration | `app/services/business_operator_service.py` |
| Audit | `app/services/business_operator_audit.py` |

---

## 5. Feature flags (AI.203)

```env
BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED=false
BUSINESS_OPERATOR_LLM_MIN_CONFIDENCE_TO_ACCEPT=0.65
```

---

## 6. Merge logic (AI.200)

1. Rule confidence ≥ threshold → `rule_based`, no LLM  
2. Rule confidence < threshold + flag off → `clarification`  
3. Flag on + valid LLM with higher confidence ≥ min_accept → `llm_fallback`  
4. Invalid LLM or low confidence → `clarification`

---

## 7. API / UI (AI.202)

Analyze/clarify responses include:

- `source`, `confidence_before`, `confidence_after`
- `llm_used`, `llm_provider`, `llm_model`

UI shows source badge and **Assisted classification** when `llm_used=true`.

---

## 8. Safe audit (AI.201)

Logged: `llm_used`, provider, model, confidence_before/after, selected_scenario, short message_preview.

Forbidden: raw prompt, raw completion, provider payload, secrets.

---

## 9. Regression (AI.204)

```bash
uv run pytest tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q
uv run pytest tests/test_phase_ai_194_business_operator_assist_regression.py -q
uv run pytest tests/test_phase_ai_184_business_operator_regression.py -q
```

---

## 10. Freeze gate

- [x] Roadmap AI.196
- [x] Contract AI.197
- [x] Prompt AI.198
- [x] LLM service AI.199
- [x] Merge AI.200
- [x] Audit AI.201
- [x] API/UI AI.202
- [x] Flags AI.203
- [x] Regression AI.204
- [x] Docs AI.205

**Verdict:** AI.196–AI.205 ready to freeze.

**Next:** LLM may evolve as richer fallback — never bypass confidence gate or user confirm.

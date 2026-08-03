# Phase AI.186 — Business Operator Assist Mode Roadmap

**Date:** 2026-06-03  
**Goal:** Safe assist layer before LLM — clarifications, confidence gate, explanation, preview, explicit confirmation.

---

## Context

AI.176–AI.185 delivered rule-based Business Operator (analyze → create campaign). Users with vague requests need a **consultant-like** flow without breaking the rule-based foundation.

---

## Assist-mode principles

| Rule | Detail |
|------|--------|
| Rule-based first | Keyword intent analyzer remains primary |
| LLM optional later | AI.196+ may add LLM fallback — not in this package |
| No auto-create | Campaign created only after user confirms |
| No hidden wizard advance | Assist does not call wizard / execution / publish |

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.186 | This roadmap |
| AI.187 | `BusinessOperatorClarification` contract |
| AI.188 | Confidence gate (default threshold 0.65) |
| AI.189 | `POST .../business-operator/clarify` |
| AI.190 | `ScenarioExplanation` in responses |
| AI.191 | `BusinessOperatorCampaignPreview` (no DB) |
| AI.192 | UI assist flow |
| AI.193 | Safe intent audit logging |
| AI.194 | Regression |
| AI.195 | Freeze audit + docs |

---

## API

```
POST /projects/{id}/business-operator/analyze
→ intent, recommendation, confidence_gate_passed,
  clarification_questions | explanation + preview

POST /projects/{id}/business-operator/clarify
Body: { previous_intent, answers: { missing_field: value } }
→ updated_intent, recommendation, gate status

POST /projects/{id}/business-operator/create-campaign
Body: { message } OR { intent } — requires confidence_gate_passed
```

---

## Confidence gate (AI.188)

When `intent.confidence < threshold` (default **0.65**):

- `confidence_gate_passed = false`
- Return `clarification_questions`
- No `preview`, no create button in UI

When gate passed:

- Return `explanation` + `preview`
- User must explicitly confirm create

---

## Safe audit (AI.193)

Log only: `intent_audit_id`, `goal`, `industry`, `confidence`, `scenario`, short `message_preview`.  
No raw full user prompt in logs.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_194_business_operator_assist_regression.py -q
```

# Phase AI.185 — General Business Operator Readiness Audit

**Date:** 2026-06-03  
**Scope:** Rule-based Business Operator — intent → scenario → campaign (AI.176–AI.184).

---

## 1. Product intent

Before AI.185 the user path was: pick scenario → create campaign → wizard → actions.

After AI.185:

```
"Мне нужны лиды для стоматологии"
        ↓
Business Operator (analyze + recommend)
        ↓
Create campaign
        ↓
Campaign Control Center / Action Center
```

This is the first layer that feels like a **marketing agency**, not a process constructor.

---

## 2. Contracts (AI.177)

`BusinessIntent`, `ScenarioRecommendation`, `BusinessOperatorAnalyzeResponse`, `BusinessOperatorCreateCampaignResponse` in `app/schemas/contracts.py`.

---

## 3. Rule-based analyzer (AI.178)

`app/domain/business_intent_analyzer.py` — keyword rules (RU/EN), no LLM.

Industries: `dental`, `restaurant`, `expert`, `saas`, `local`.

---

## 4. Scenario recommendation (AI.179)

`app/services/business_scenario_recommendation_service.py` — `recommended_scenario`, `alternative_scenarios`, `reason`, `confidence`.

Maps to existing five scenarios in `app/marketing/scenarios/registry.py`.

---

## 5. API (AI.180–AI.182)

```
POST /projects/{id}/business-operator/analyze
POST /projects/{id}/business-operator/create-campaign
```

Service: `app/services/business_operator_service.py`  
Routes: `app/api/routes/business_operator.py`

Create campaign reuses `CampaignLayerService.create` with scenario from recommendation.

---

## 6. Provenance (AI.183)

Operator-created campaigns store:

```json
metadata.source_business_intent: {
  goal, industry, business_type, campaign_type,
  confidence, recommended_scenario, alternative_scenarios, reason
}
```

Sanitized via `sanitize_payload`.

---

## 7. UI (AI.181)

`web/src/components/agent-chat/business-operator-panel.tsx` — message input, analyze, scenario + campaign name, **Create campaign**.  
Integrated in `marketing-plans-panel.tsx`; focuses Action Center on new campaign.

---

## 8. Invariants

| Rule | Status |
|------|--------|
| No LLM in operator v1 | ✓ |
| No auto wizard / execution / publish | ✓ |
| Frozen pipeline (AI.39) unchanged | ✓ |
| Inbound text sanitized | ✓ |
| Not a new marketing specialist | ✓ |

---

## 9. Regression (AI.184)

```bash
uv run pytest tests/test_phase_ai_184_business_operator_regression.py -q
```

Cases: dental, restaurant, expert, SaaS, local — analyze + create with `source_business_intent`.

---

## 10. Freeze gate

- [x] Roadmap AI.176
- [x] Contracts AI.177
- [x] Analyzer AI.178
- [x] Recommendation AI.179
- [x] API AI.180–AI.182
- [x] UI AI.181
- [x] Provenance AI.183
- [x] Regression AI.184
- [x] Docs AI.185

**Verdict:** AI.176–AI.185 ready to freeze.

# Phase AI.215 — Campaign Brief Intake Readiness Audit

**Date:** 2026-06-03  
**Scope:** Minimal business brief before campaign creation (AI.206–AI.214).

---

## 1. Product intent

Business Operator already resolves intent and scenario. **Campaign Brief Intake** collects agency-style inputs before a campaign is created — plans and wizards no longer run on a single phrase.

---

## 2. Principles (AI.206)

| Rule | Status |
|------|--------|
| No LLM plan generation | ✓ |
| No execution changes | ✓ |
| In-memory brief draft on analyze/clarify | ✓ |
| Create campaign requires confirmed `brief_id` | ✓ |
| Intent confidence gate still applies | ✓ |
| Brief completeness gate (default 100) | ✓ |

---

## 3. Contracts (AI.207)

`CampaignBrief` — business_name, industry, offer, target_audience, geography, channels, budget_range, deadline, constraints, success_metric, goal, status (`draft` \| `confirmed` \| `archived`).

`CampaignBriefCompleteness` — score 0–100, threshold, `passed`, `missing_questions`.

`CampaignBriefQuestion` — field, question, optional options, required flag.

---

## 4. Completeness engine (AI.208–AI.209)

| Field | Weight |
|-------|--------|
| industry | 25 (required) |
| offer | 25 (required) |
| target_audience | 25 (required) |
| goal | 25 (required) |
| geography, channels, budget_range, deadline | optional bonus |

Below threshold → `missing_questions` returned with analyze/complete responses.

---

## 5. Implementation

| Component | Path |
|-----------|------|
| Contracts | `app/schemas/contracts.py` |
| Completeness | `app/domain/campaign_brief_completeness.py` |
| Draft merge | `app/domain/campaign_brief_draft.py` |
| Persistence | `app/db/models/campaign_brief.py`, `app/db/repositories/campaign_briefs.py` |
| Service | `app/services/campaign_brief_service.py` |
| Operator integration | `app/services/business_operator_service.py` |
| Plan provenance | `app/services/scenario_wizard_service.py` |
| API | `app/api/routes/business_operator.py` |
| UI | `web/src/components/agent-chat/business-operator-panel.tsx` |
| Migration | `alembic/versions/20260603_0025_campaign_brief_intake_phase_ai_211.py` |

---

## 6. Flow (AI.210–AI.212)

1. `POST .../business-operator/analyze` → intent + `brief_draft` + `brief_completeness`
2. Optional `POST .../clarify` for intent
3. `POST .../brief/complete` → merge answers (no DB)
4. `POST .../brief/confirm` → persist confirmed brief (gates: confidence + completeness)
5. `POST .../create-campaign` with `{ intent, brief_id }` → campaign + link brief

---

## 7. Provenance (AI.213)

- `Campaign.metadata.source_campaign_brief_id`
- `MarketingPlan.project_context.campaign_brief_summary` — safe sanitized summary on wizard plan step

---

## 8. Configuration

```env
CAMPAIGN_BRIEF_COMPLETENESS_THRESHOLD=100
```

---

## 9. Regression (AI.214)

```bash
uv run pytest tests/test_phase_ai_214_campaign_brief_intake_regression.py -q
uv run pytest tests/test_phase_ai_184_business_operator_regression.py tests/test_phase_ai_194_business_operator_assist_regression.py tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q
```

Cases: vague → missing questions; dental → partial brief; answers improve score; create blocked without confirmed brief; confirmed brief → campaign provenance; wizard plan gets brief context.

---

## 10. Known limits

- Brief draft is rule-based from intent — no LLM brief generation.
- Optional brief fields do not block create when required score passes threshold.
- UUID values in metadata are preserved through PII sanitizer (phone regex no longer masks UUIDs).

---

## 11. Verdict

**Ready** for the next phase (plan/scenario work with richer campaign context).

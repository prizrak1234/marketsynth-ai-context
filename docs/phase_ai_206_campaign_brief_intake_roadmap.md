# Phase AI.206 — Campaign Brief Intake Roadmap

**Date:** 2026-06-03  
**Goal:** Collect a minimal business brief before campaign creation — no plan generation, no execution.

---

## Context

Business Operator (AI.176–AI.205) resolves intent and scenario. Without a brief, marketing runs on a single phrase. **Campaign Brief Intake** adds agency-style input gathering first.

---

## Principles

| Rule | Detail |
|------|--------|
| No LLM plan generation | Brief intake only |
| No execution | Wizard/execution unchanged until user acts |
| In-memory draft first | Analyze/clarify return `brief_draft` |
| Confirmed brief required | Create campaign needs `brief_id` |
| Confidence gate still applies | Intent + brief completeness |

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.206 | This roadmap |
| AI.207 | `CampaignBrief` contract |
| AI.208 | Completeness engine (0–100) |
| AI.209 | `missing_questions` when below threshold |
| AI.210 | Brief draft in analyze; create gated |
| AI.211 | Persist brief linked to campaign |
| AI.212 | UI brief fields + confirm |
| AI.213 | Provenance on campaign + plan context |
| AI.214 | Regression |
| AI.215 | Freeze audit |

---

## API

```
POST .../business-operator/analyze        → brief_draft + brief_completeness
POST .../business-operator/brief/complete → merge answers (no DB)
POST .../business-operator/brief/confirm  → persist confirmed brief
POST .../business-operator/create-campaign → requires brief_id
```

---

## Required brief fields

`industry`, `offer`, `target_audience`, `goal` — score 25 each, threshold default **100**.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_214_campaign_brief_intake_regression.py -q
```

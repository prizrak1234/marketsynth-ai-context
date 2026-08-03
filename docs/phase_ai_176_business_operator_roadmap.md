# Phase AI.176 — General Business Operator Roadmap

**Date:** 2026-06-03  
**Goal:** Top-level operator that understands a business request, picks a scenario, and creates a campaign — not another marketing specialist.

---

## Context

Through AI.175 BotFazer has Infrastructure → Campaign → Control Center → Action Center. Users still assemble campaigns manually (scenario picker, wizard, actions).

**General Business Operator** is the first layer that feels like a marketing agency: the user describes a business need; the system recommends a scenario and creates a campaign.

---

## Role

| Is | Is not |
|----|--------|
| General Business Operator | New marketing specialist |
| Top-level orchestrator | Hidden automation |
| Rule-based intent first (AI.178) | LLM magic in v1 |

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.176 | This roadmap |
| AI.177 | `BusinessIntent` contract |
| AI.178 | Rule-based intent analyzer |
| AI.179 | Scenario recommendation engine |
| AI.180 | `POST .../business-operator/analyze` |
| AI.181 | UI — message → scenario + campaign name + Create |
| AI.182 | Create Campaign → Campaign + scenario + Control Center |
| AI.183 | `source_business_intent` on campaign metadata |
| AI.184 | Regression — dental, restaurant, expert, SaaS, local |
| AI.185 | Freeze audit + docs |

---

## API

```
POST /projects/{id}/business-operator/analyze
Body: { "message": "..." }
→ intent, recommended_scenario, recommended_campaign_name, recommendation

POST /projects/{id}/business-operator/create-campaign
Body: { "message": "..." }
→ campaign, intent, recommendation, control_center
```

---

## User flow (after AI.185)

```
"Мне нужны лиды для стоматологии"
        ↓
Business Operator (analyze + recommend)
        ↓
[Создать кампанию]
        ↓
Campaign + Control Center / Action Center
```

---

## Invariants

- Rule-based analyzer only — no LLM in this package.
- Does not auto-run wizard, execution, or publish.
- Reuses existing `CampaignLayerService` and scenario registry.
- Inbound text sanitized via `sanitize_text` / `sanitize_payload`.
- Frozen pipeline (AI.39) unchanged.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_184_business_operator_regression.py -q
```

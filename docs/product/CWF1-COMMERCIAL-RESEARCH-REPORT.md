# CWF.1 — Commercial Research Report Architecture

**Status:** `waiting_for_owner_validation`

## Problem

Commercial users saw engine diagnostics (queries, coverage statuses, stop reasons) instead of a professional marketing research conclusion.

## Solution: dual report mode

| Mode | Audience | Contents |
|------|----------|----------|
| **Customer Report** | End user | Executive summary, confirmed/unconfirmed findings, confidence, coverage, verdict, strategic questions |
| **Internal Diagnostics** | Developer / operator | Queries, gap codes, MCP stats, raw evidence, pipeline phases |

Built in:
- `app/business_idea_validation/customer_report.py`
- `app/business_idea_validation/internal_report.py`

Exposed on `BusinessIdeaValidationOutput`:
- `customer_report`
- `internal_diagnostics`

## Cascade pipeline

`research_cascade.py` — full search before verdict:

```
direct → indirect → international → local → adjacent → transferability
```

Skill runs up to 32 search / 40 fetch calls across phases (no early stop on first failure).

## UI

- `business-validation-result-card.tsx` — **Customer Report only**
- `business-validation-developer-panel.tsx` — collapsible **Engine Diagnostics**

Forbidden in commercial UI: search queries, raw gap codes, engine stop messages, tier labels.

## Regression

```bash
uv run pytest tests/test_cwf1_commercial_research_report.py \
  tests/test_product_01_3b_2a_research_execution_quality.py -q
```

## Owner acceptance

Re-run binding SaaS/RF scenario. Result must read as agency-grade analytical conclusion, not search engine debug output.

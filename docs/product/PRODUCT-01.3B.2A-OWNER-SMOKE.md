# PRODUCT-01.3B.2 / 2A — Owner Visual Smoke

**Program:** [PRODUCT-FINISH-01](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md) — Step A  
**Status:** `waiting_for_owner_validation` (second smoke after repair)

**First smoke:** FAIL (2026-07-25) — see [PRODUCT-01.3B.2A-RESEARCH-EXECUTION-QUALITY.md](./PRODUCT-01.3B.2A-RESEARCH-EXECUTION-QUALITY.md)

**Repair implemented:** query_strategy, research_decomposition, commercial_relevance; interim conclusion fix.

---

## Binding scenario

| Field | Value |
|-------|--------|
| Idea | AI-маркетинговое агентство полного цикла — заменяет агентство: исследование рынка, ЦА, конкуренты, оффер, стратегия запуска, материалы |
| Product | SaaS |
| Audience | маркетологи, блогеры |
| Geography | РФ |
| Pricing | 200–900 USD / month |
| Competitors | неизвестно |
| Stage | разработка |
| Goal | проверить жизнеспособность идеи |

Flow: новый проект → intake confirm → «Начать исследование» → дождаться terminal state.

---

## PASS criteria

1. **Seven research directions** visible in coverage (market, demand, competitors, audience, pricing, local_context, commercial_risks).
2. **Real research attempted** — per-direction status shows researched / partial / insufficient, not only generic failure.
3. **Useful partial findings** — not empty refusal; at least some established facts or signals when any source exists.
4. **User hypotheses** — pricing and audience marked as user hypothesis, not market fact.
5. **Concrete remediation questions** (≥3) — ICP, use case, competitors, etc.
6. **Plain-language stop reason** if insufficient — not raw codes.
7. **Forbidden absent:** enum labels, hashes, internal IDs, raw error codes, raw URLs, markdown in findings, English diagnostic tokens.
8. **Blocked absent:** verdict UI, confidence %, Launch Pack, Offer Builder CTA.
9. **Overall:** reads as **marketing research**, not error log.

---

## Owner verdict template

```
PRODUCT-01.3B.2A owner visual smoke: PASS
```

or

```
PRODUCT-01.3B.2A owner visual smoke: FAIL

Проблемы:
1. ...
2. ...
```

---

## After verdict

| Outcome | Next slice |
|---------|------------|
| **PASS** | [PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md](./PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md) |
| **FAIL** | PRODUCT-01.3B.2A — Research Execution Quality Repair (implementation) |

**Do not open PRODUCT-01.3C** until owner PASS on research quality + QA harness in place.

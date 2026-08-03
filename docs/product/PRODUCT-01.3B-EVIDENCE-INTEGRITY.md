# PRODUCT-01.3B — Evidence Integrity & Real Research Run

**Status:** `01.3B.1 partial` — presentation OK; research value blocked → **01.3B.2 OPEN** — code complete, **not accepted**  
**Priority:** P0 (commercial honesty)  
**Depends on:** PRODUCT-01.3A (`conditionally_accepted_as_intake_only`)  
**Blocks:** PRODUCT-01.3C/D/E until owner PASS on [01.3B.2](./PRODUCT-01.3B.2-RESEARCH-COVERAGE-QUERY-STRATEGY.md)

**Process rule:** No "Final Report". Cursor stops at *Waiting for Owner Validation*. Zero 01.3C code until PASS or defect list.

**01.3A acceptance record:** [PRODUCT-01.3A-ACCEPTANCE-RECORD.md](./PRODUCT-01.3A-ACCEPTANCE-RECORD.md)

---

## Owner findings driving 01.3B (2026-07-24)

Downstream smoke after intake confirm **FAIL** — report unrelated to submitted idea (Skillbox/outsourcing/YouTube garbage), markdown/URLs in «Подтверждённые выводы», decorative 82% confidence vs «недостаточно данных», final report while stages incomplete, **«Начать исследование» does not start a real research run**.

These are **not** 01.3A intake defects. Do not block 01.3B on another full-report 01.3A re-smoke.

---

## Runtime finding (add to scope)

### P0 — `research_start_action_not_bound_to_real_research_run`

- «Начать исследование» must create/bind a distinct research run identity
- Must not replay stale BIV output from prior context/hash
- Final report forbidden until research run reaches terminal state
- Report must reference `analysis_context_id` + `input_snapshot_hash`
- No final report while stage machine shows incomplete stages (coordination with 01.3D)

**Area:** BIV run orchestration, research endpoints, workspace home actions, run lineage

---

## Objective

Restore commercial honesty of BIV **evidence** — not verdict, not confidence, not full report UI.

The system must never present search snippets, navigation text, scraped garbage, markdown fragments, unrelated URLs, or unsupported statements as **confirmed** business evidence.

**Authoritative regression:** owner screenshot — «Подтверждённые выводы» contained `To main content`, markdown, raw URLs, navigation fragments, unrelated snippets.

---

## Primary principle

```
SOURCE ≠ EVIDENCE
SEARCH RESULT ≠ FACT
URL ≠ PROOF
SNIPPET ≠ VERIFIED CLAIM
```

Every displayed statement belongs to exactly one evidence class.

---

## Required evidence classes

| Class | Role |
|-------|------|
| `source_reference` | Citation anchor only |
| `observation` | Extracted from source |
| `structured_fact` | Normalized fact |
| `market_signal` | Demand/competition signal |
| `competitor_signal` | Competitor-specific |
| `customer_signal` | Audience/segment |
| `economic_signal` | Pricing/unit economics |
| `risk_signal` | Risk factor |
| `hypothesis` | Unverified — **not** confirmed |
| `unsupported_claim` | Failed validation |
| `research_gap` | Missing coverage |

**Forbidden:** generic string evidence, mixed markdown/URLs, unclassified search snippets.

---

## Implementation priorities (ordered)

### P0 — Sanitization pipeline

Deterministic sanitizer removing:

- Navigation: `To main content`, menus, breadcrumbs, cookie/login chrome
- Markdown artifacts, HTML entities, anchor garbage
- Tracking URLs / UTM params
- Duplicate whitespace, repeated titles, empty bullets
- Site chrome (header/footer boilerplate)

**Area:** `app/business_idea_validation/extraction.py`, new `sanitization.py`

### P0 — Source vs claim separation

Each item: `source` + `claim` + `support` + `limitations` — never one merged paragraph.

**Area:** `findings.py`, `skill.py`, contracts

### P0 — Classification gate

Claim → `confirmed` only if: supported + quality gate + relevance. Else `hypothesis` or `research_gap`. Never silent upgrade.

**Area:** `findings.py`, `audience_segmentation.py` (`audience_has_support` bug)

### P0 — URL policy

No naked URLs in findings. Source section only: title, domain, publication, date.

### P1 — Source quality tiers

| Tier | Treatment |
|------|-----------|
| A | Gov, official stats, industry reports, peer-reviewed |
| B | Trusted industry media, major platforms |
| C | Blogs, marketing — supporting context only |
| D | Unknown, aggregators, spam — **reject** |

Only A/B may support confirmed observations.

### P1 — Relevance filter

Reject vs idea, audience, geography, market, industry when generic SEO/landing/index/search portal.

### P1 — Duplicate merge + contradiction surfacing

Merge duplicates (strongest source). Conflicts → both shown, «manual review recommended».

---

## Evidence contract (target)

```yaml
evidence_id:
type:                    # taxonomy enum
statement:
classification:          # confirmed | hypothesis | gap
source_reference:
source_quality:          # A | B | C | D
publication_date:
market_scope:
geography:
industry:
support_level:
limitations: []
relevance_score:
sanitized: true
verified: bool
hash:
```

No raw `snippet` field in customer-facing output.

---

## Report changes (minimal for 01.3B)

Replace flat «Подтверждённые выводы» blob with **structured evidence cards**:

- Title · Class · Statement · Support · Source · Limitations
- No markdown, no URLs in statement body
- Hypotheses and gaps in separate sections

Full verdict/confidence UI → **01.3C**. Stage honesty → **01.3D**.

---

## API

Return structured evidence objects. Frontend formats cards. Backend owns classification.

Extend `BusinessIdeaValidationFinding` / evidence summaries in `contracts.py` first.

---

## Tests

**New:** `tests/test_product_01_3b_evidence_integrity.py`

Minimum: navigation removed, `To main content` removed, markdown/URLs removed, SEO garbage rejected, duplicate merge, unsupported → hypothesis, tier D rejected, contradiction detected, source≠claim, deterministic hash, UTF-8 RU/EN preserved, **owner screenshot regression not reproducible**.

Regressions: BIV suite, Offer blocked-path, ruff, typecheck.

---

## Non-goals (01.3B)

- Confidence % redesign (01.3C)
- Verdict proceed/revise rules (01.3C)
- Cosmetic stage progress honesty only without evidence fix (01.3D — coordinate, do not defer all stage UI)
- Launch Pack / Offer / Media / Content Strategy / Higgsfield

## In scope additions (owner 2026-07-24)

1. Source/claim separation
2. Snippet sanitization
3. Relevance filter vs idea/audience/geography
4. Research-run identity + lineage
5. Bind «Начать исследование» to real research run
6. No final report before research terminal state
7. Stale report must not reuse for new context
8. Report bound to `analysis_context_id` / `input_snapshot_hash`
9. Raw markdown/URLs/navigation/CTA forbidden in customer UI
10. Structured evidence objects only

Verdict scoring unchanged except: **do not emit final verdict from invalid evidence** (full redesign → 01.3C).

---

## Definition of done

1. No scraped garbage, markdown, naked URLs, navigation text in findings
2. No unsupported statement labeled confirmed
3. Evidence structured; source separated from claim
4. Deterministic hashes preserved
5. Tests green
6. **Stop** — do not start 01.3C in same PR

---

## Code map (current defects)

| Defect | Primary files |
|--------|---------------|
| Raw scrape in findings | `extraction.py`, `skill.py` |
| Auto-accept evidence | `skill.py` `_create_accepted_evidence()` |
| Hypothesis as support | `audience_segmentation.py` `audience_has_support()` |
| Mislabeled UI section | `business-validation-result-card.tsx`, `ru.ts` |
| Snippet → finding | `findings.py` |

---

## Related docs

- [BIV-EVIDENCE-CONTRACT.md](./BIV-EVIDENCE-CONTRACT.md) (create with implementation)
- [BIV-SOURCE-SANITIZATION.md](./BIV-SOURCE-SANITIZATION.md) (create with implementation)
- [PRODUCT-01.3A-INTAKE-HYDRATION-CONSENT.md](./PRODUCT-01.3A-INTAKE-HYDRATION-CONSENT.md)

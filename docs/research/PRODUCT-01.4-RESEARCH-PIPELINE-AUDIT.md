# PRODUCT-01.4 — Research Pipeline Audit

> Owner smoke funnel (Marketsynth, run `90a0d5eb-…`): **116 URLs → 40 extractions → 4 evidence → partial_research**  
> Date: 2026-07-31 · Task: PRODUCT-01.4-COMMERCIAL-FOUNDATION-01

## Executive summary

The pipeline **worked as designed**; the loss is concentrated in **fetch budget**, **source relevance**, **claim extraction**, and **publisher independence** gates — not infrastructure failure.

**Slice fixes (confirmed bottlenecks only):**

| Fix | Rationale | Expected impact |
|-----|-----------|-----------------|
| Publisher-diverse fetch ordering | `high_impact_insufficient_sources` needs ≥2 independent publisher groups per high-impact finding | More diverse sources within same 40-fetch budget |
| `FETCHES_PER_CATEGORY` 2→3 | Stopped early per query while candidates remained | +~50% fetch attempts per search query |
| Claim fallback up to 2 sentences | Keyword filter dropped most sentences; fallback yielded only 1 claim | More claim candidates → more evidence |
| Partial `next_steps` + richer interim copy | Partial output had empty `next_steps[]` | User gets actionable guidance without new run |

**Not changed (by design):** traceability gate, coverage gate floors, commercial relevance at claim level — loosening would increase hallucination risk.

---

## Stage funnel

| Stage | Input | Output (owner run) | Est. loss | Primary cause |
|-------|-------|-------------------|-----------|---------------|
| Discovery | Intake | ~35 plan items | Plan >> budget | Cascade generates more queries than `max_search_calls=32` |
| Search | Queries | **116 URL candidates** | — | ~29 searches × 4 candidates |
| Fetch | 116 candidates | **~40 extractions** | ~66% | Budget cap 40; dedup; fetch/extraction rejections |
| Relevance | 40 bodies | ~8–15 sources (est.) | ~60–80% | `assess_source_relevance` token overlap + commercial hints |
| Claims | Sources | ~8–16 claims (est.) | ~50% | Category keywords; max 2/source; atomic rules |
| Evidence | Claims | **4 accepted** | ~50–75% | Commercial filter; tier D/C; min excerpt 24 chars |
| Findings | 4 evidence | Category findings | — | Only CONFIRMED in main findings |
| Verdict gate | Findings | **FAIL** | — | `high_impact_insufficient_sources` (<2 publisher groups) |
| Delivery | FAIL | **partial_research** | — | `can_deliver_partial_research` |

---

## Loss hotspots (file references)

### Fetch budget (`skill.py`)
- `max_fetch_calls=40` (`config.py`)
- `FETCHES_PER_CATEGORY` — was 2, now **3**
- `seen_urls` dedup
- Extraction rejections: `content_extraction.py` (80 char min, boilerplate, nav-only)

### Relevance (`relevance.py:76-165`)
- Generic SEO hosts rejected
- Token overlap `< 0.08` → drop before claims
- **Largest mid-pipeline drop** — deferred softening (medium cost, needs A/B)

### Claims (`extraction.py`)
- Category keyword hard filter
- Fallback: was 1 claim max → now **2**

### Evidence (`evidence_validation.py`, `commercial_relevance.py`, `classification.py`)
- Min 24 char excerpt
- Tier D → UNSUPPORTED
- Commercial relevance per claim

### Independence (`finding_traceability.py:56-59`)
- High-impact categories require **≥2 source groups**
- Owner run: 4 evidence likely from ≤4 domains but not 2+ per category finding

---

## Metrics (before / after slice)

| Metric | Before (owner) | After (expected) | Verification |
|--------|----------------|------------------|--------------|
| Fetches per query | ≤2 | ≤3 | Unit + next owner run |
| Publisher diversity in fetch order | URL order only | Unseen domains first | `skill.py` ordering |
| Claims from keyword-miss body | 1 (fallback) | 2 (fallback) | `test_product_01_4_*` |
| Partial `next_steps` | `[]` | 2–4 actionable steps | `test_product_01_4_*` |
| Accepted evidence (same idea) | 4 | TBD — owner re-run | Not verified in this slice |

---

## Deferred (next slices)

1. **Relevance gate softening** — borderline sources to claim stage (medium cost)
2. **Investigation terminalization** after terminal BIV run
3. **Remove duplicate commercial filter** in `build_findings` (low cost maintenance)

---

## Out of scope (this task)

Telegram, Launch, HR, Legal, new agents, MCP, billing.

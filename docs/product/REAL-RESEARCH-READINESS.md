# REAL-RESEARCH-READINESS (Program)

**Status:** `implementation_in_progress`  
**Active slice:** **[REAL-RESEARCH-HARDENING-01](./RESEARCH-PIPELINE-HARDENING.md)**  
**Priority:** **sole P0** — everything else frozen until owner PASS

## One-line goal

Довести Research Engine до состояния, при котором он самостоятельно получает, извлекает, нормализует и использует доказательства для формирования коммерческого аналитического отчёта с полной трассируемостью источников.

## Where we are (honest)

| Layer | Maturity |
|-------|----------|
| UI | ~100% |
| Workflow / Golden Path | ~100% |
| **Research Engine** | **~40%** ← P0 |
| Commercial Readiness | ~30% |

Weakest part: **research quality**, not interface or architecture.

## What this program is NOT

- ❌ «Fix Firecrawl» as the whole slice
- ❌ Provider smoke PASS as Definition of Done
- ❌ New Campaign / Direct / Pre-Launch features

## What this program IS

Full **Research Pipeline Hardening** across six stages — see **[RESEARCH-PIPELINE-HARDENING.md](./RESEARCH-PIPELINE-HARDENING.md)**.

```
Discovery → Fetch → Extract → Normalize → Evidence → Reasoning → Verdict → Report
```

True PASS requires pipeline metrics (search ≥95%, fetch ≥90%, extraction ≥95%, evidence coverage ≥80%, citation 100%, hallucination 0) — not credential probes alone.

## Depends on

- BIV Golden Path Stabilization — `owner_accepted` ✅

## Blocks

- QA-01
- PRE-LAUNCH-READINESS-01 (implementation)
- Campaign Plan / Direct / Ads / SEO / HR / Legal / CRM / Auto Publish

## Operator commands

See [RESEARCH-PIPELINE-HARDENING.md](./RESEARCH-PIPELINE-HARDENING.md) and sections below for scripts.

### Provider precondition (not PASS)

```bash
uv run python scripts/real_research_provider_smoke.py
```

### Real case

```bash
uv run python scripts/biv_real_case_smoke.py --case marketsynth_saas --timeout-seconds 900
```

### Tests

```bash
uv run pytest tests/test_real_research_readiness.py -q
```

## Implementation map (current)

| Component | Path | Stage |
|-----------|------|-------|
| Query decomposition | `query_strategy.py`, `research_decomposition.py` | Discovery |
| Search/fetch loop | `skill.py`, `mcp/client.py` | Discovery, Fetch |
| Fetch providers | `firecrawl_fetch.py`, `xmlriver_search.py` | Fetch |
| Extract/sanitize | `sanitization.py`, `source_quality.py` | Extract |
| Evidence rules | `evidence_validation.py`, `evidence_contract.py` | Evidence |
| Findings/verdict | `findings.py`, `commercial_verdict.py` | Reasoning |
| Report/export | `customer_report.py`, `report_export.py` | Report |
| Validation gates | `real_research_readiness.py` | All |
| Provider smoke | `scripts/real_research_provider_smoke.py` | Precondition |
| Case runner | `scripts/biv_real_case_smoke.py` | E2E |

**Gap (HARDENING-01):** closed — fetch ledger, pipeline metrics, fallback contour, real case executed.  
**Active P0:** [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md) (`HARDENING-02`) — claim extraction pipeline; 40 docs → 1 evidence measured on run `5eaa7519`.

## Baseline incident

Run `8038e2a7` (2026-07-28): **32 search / 0 fetch** → 0 evidence → HOLD 10%. API `succeeded` but pipeline **FAIL**.

Artifact: `artifacts/real-research-readiness/marketsynth-export-8038e2a7.txt`

## After owner PASS

1. QA-01 (commercial acceptance harness)
2. [PRE-LAUNCH-READINESS-01](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) implementation
3. Campaign Plan → [Campaign Mode Selector](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md) → [Ad Format Selection](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) → Yandex Direct Execution

## Owner decision

**pending** — waiting for REAL-RESEARCH-HARDENING-01 true PASS on Marketsynth real case.

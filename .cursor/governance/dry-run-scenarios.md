# Governance dry-run scenarios (CURSOR-GOVERNANCE-01)

Reproducible read-only checks. No product code changes.

---

## Scenario 1 — Planning Gate on RUNTIME-01C (read-only)

**Prompt:** "GO PRODUCT-01.3B-RUNTIME-01C" (already owner-approved)

**Expected Planning Gate behavior:**
- Task ID: RUNTIME-01C / PRODUCT-01.3B-RUNTIME-01C
- Active priority: RUNTIME-01C (from `knowledge/06_CURRENT_STATE.md`)
- Files: `skill.py`, `business_idea_validation_service.py`, `partial_research_delivery.py`, `output_enrichment.py`, frontend polling/workspace, `tests/test_runtime_01c_partial_output.py`
- Does **not** redesign architecture; maps spec → repo
- Contradictions: none if spec matches partial contract (`status=failed`, `output!=null`, `result_kind=partial_research`)
- Owner decision required: **no** (spec approved)

**Pass criteria:** Preflight emitted; no scope expansion to 01D UI or new status enum.

**Executed 2026-07-30:** PASS — spec maps to existing gate failure points in skill/service; no new DB schema required.

---

## Scenario 2 — Synthetic bad diff (product FAIL)

**Synthetic change:** Set `status=succeeded` when `research_terminal_state=succeeded_insufficient` and create Launch Pack eligibility.

**Expected reviewer verdicts:**
| Reviewer | Verdict | Reason |
|----------|---------|--------|
| Product | **FAIL** | False success; Golden Path opens verdict without customer_report |
| Runtime | **FAIL** | Breaks failed+partial contract; metrics/hydration regression |
| Test | **FAIL** | Missing negative assertion on partial contract |
| Architecture | **FAIL** or non-blocking | Scope/status model change vs approved 01C |
| Security | PASS/N/A | Unless auth touched |

**Composite:** **FAIL**

---

## Scenario 3 — Security synthetic diff

**Synthetic change:** `log.info("api_key=%s", settings.openai_api_key)` in service.

**Expected:**
- Security reviewer: **FAIL** — secret in logs, `path:line`
- Composite: **FAIL**

---

## Scenario 4 — Benign docs-only diff

**Change:** Edit `docs/cursor/CURSOR-GOVERNANCE.md` typo only.

**Expected:**
- All reviewers: **PASS** or explicit N/A (no product surface)
- Composite: **PASS**
- Planning Gate: lightweight skip OK

---

## How to replay

1. For Scenario 1: paste approved Task ID; require PRE-IMPLEMENTATION CHECK only.
2. For Scenarios 2–3: paste synthetic diff description; run `marketsynth-composite-review` skill.
3. For Scenario 4: edit governance doc; confirm no composite review required.

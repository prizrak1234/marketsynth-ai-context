# Workflows

> **Business workflows** — not n8n execution. Checklists and commercial paths.  
> **Last updated:** 2026-07-29

---

## CWF.1 — Canonical Commercial Workflow (active)

```
Idea
  ↓ Intake + confirm (PRODUCT-01.3)
Research + Evidence collection
  ↓ Gap-directed coverage
Verdict (GO / CONDITIONAL / PILOT / HOLD / NO_GO)
  ↓ Human acceptance
Offer Builder
  ↓ Review
Launch Plan
  ↓
3 Content Assets (Telegram posts)
  ↓ Optional
Visuals (1–3)
  ↓
Telegram Approval
  ↓
Real Publication
  ↓
Delivery Evidence (persisted)
```

**Spec gaps:** [docs/product/CWF-SKILL-INTEGRATION-GAPS.md](../docs/product/CWF-SKILL-INTEGRATION-GAPS.md)  
**Intent entry:** [docs/product/CWF.1a-intent-entry-ux.md](../docs/product/CWF.1a-intent-entry-ux.md)

---

## BIV workflow (CMVP.1)

```
User clicks «Проверить идею»
  → Show saved idea OR empty intake
  → User confirms/edits intake
  → Specificity gate (01.3A)
  → Analysis execution
  → Structured report sections
  → Verdict only if gates pass
```

**Integrity repair (P0):** [docs/product/PRODUCT-01.3-BIV-INTAKE-EVIDENCE-REPORT-INTEGRITY.md](../docs/product/PRODUCT-01.3-BIV-INTAKE-EVIDENCE-REPORT-INTEGRITY.md)

---

## Marketing campaign workflow (frozen AI.256–265)

```
Business Operator intent
  → Scenario selection
  → Campaign create (requires confirmed brief_id)
  → Control Center (health, next_action)
  → Action Center (explicit execute)
  → Skill runs (one at a time)
  → Supervisor review (read-only)
  → Workflow checklist run (no auto-execution)
```

Templates: `lead_gen_campaign`, `content_machine`, `offer_validation`, etc.

---

## Scenario wizard workflow (AI.136–145)

Manual step wizard — **one step per** `POST .../scenario-wizard-runs/{id}/advance`:

```
Create wizard run
  → Approve plan step
  → Execute specialist step
  → Asset step
  → Package step
  → Dry-run job step
  (each advance = single explicit action)
```

---

## Content → Media → Publishing (frozen)

```
ContentAsset (from approved plan)
  → MediaBrief (approved)
  → MediaGenerationJob (mock or OpenAI Images)
  → PublicationPackage (approved)
  → PublicationJob (dry-run or real Telegram)
  → Scheduler due scan (explicit dispatch, no worker)
```

**Telegram real send:** gated — bot token + human approval.  
**No Instagram/LinkedIn.**

---

## Video Studio workflow (frozen VS.2A)

```
Reference visuals / image input
  → Video clip request
  → Preflight + capabilities check
  → Paid smoke execute (explicit_confirmation=true)
  → Persistence in Commercial Home
  → Owner preview (?owner_preview=video)
```

---

## Identity workflow (H2.8E, gated)

```
Reference set admission
  → Manifest (immutable, max 5 refs)
  → Preflight conditions
  → Qualification run
  → Paid approval choice
  → Provider transmit (honest lineage)
```

**Product gate:** owner person recognition in real diagnostic.

---

## Approval workflows (cross-cutting)

| Gate | Before |
|------|--------|
| Human Approval | Irreversible/paid execution |
| Brief completeness | Campaign create |
| MediaBrief approved | Media generation |
| PublicationPackage approved | Publication job |
| BIV intake confirmed | Analysis run |
| Verdict substantiation | Verdict display |

---

## Automation (reference only)

| System | Role |
|--------|------|
| n8n workflow library | 50 sanitized templates — download/draft JSON only |
| Make/n8n runtime | **Not** default execution engine |
| Webhooks | `app/api/webhooks.py` — integration boundary |

---

## Research workflow (KG.3 / H2.9A)

```
web_source_collection (bounded, read-only)
  → Source Candidate collection
  → Explicit admission → draft Knowledge candidate only
  (No auto Evidence, verdict, campaign, or publication)
```

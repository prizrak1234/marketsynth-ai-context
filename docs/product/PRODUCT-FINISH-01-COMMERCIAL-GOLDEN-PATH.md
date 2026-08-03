# PRODUCT-FINISH-01 — Commercial Golden Path Completion

**Status:** `active` — replaces horizontal micro-phase expansion  
**Objective:** One complete, customer-usable workflow — not twenty partial directions without extraction.

---

## Golden path (v1 definition of «fully working»)

```
New project
  → confirmed intake
  → real market research
  → structured evidence
  → honest verdict
  → offer generation
  → human approval
  → Telegram content draft
  → human edit / approval
  → native Telegram publication
  → message_id + Evidence
  → reload + history restore
```

**In scope for v1:** BIV → Verdict → Offer → Telegram text publish.  
**Frozen until golden path ships:** Higgsfield, multi-channel, Knowledge Core marketplace, new professions, generic Skill runtime, HR/Legal, video, site builder.

---

## What «fully working v1» means

### Functionally
User can register → create project → describe idea → confirm intake → get **real** research → get **argued** verdict → prepare offer → approve offer → create Telegram post → edit & approve → connect channel → publish → see `message_id` → reload and continue → return to project history.

### Technically
- PostgreSQL migrates clean to head
- Backend + frontend start with one command each
- No mock in customer path
- No stale processes / manual DB swap
- E2E + tenant isolation pass
- Approval cannot be bypassed
- Customer-safe errors; state restores on reload
- Secrets never in UI/logs

### Commercially
- Landing promises match product behavior
- Report is useful; verdict is honest
- Offer usable after light edit
- Telegram post actually publishable
- No hidden stubs or dead buttons

---

## Program rules

1. **No new infrastructure** unless it directly blocks the golden path.
2. **No Higgsfield** until text publication path is production-ready.
3. **No new professions**, Knowledge Core, marketplace, or generic assistant detours.
4. **No phase complete** without **owner browser PASS**.
5. Cursor statuses only:
   - `implemented`
   - `automated_verified`
   - `browser_ready`
   - `waiting_for_owner_validation`
   - `owner_accepted`
6. Every step includes: backend tests, frontend typecheck, focused E2E, customer-visible contract checks, live browser prep, **owner acceptance**.
7. Customer UI: no raw enums, hashes, IDs, URLs, markdown, technical errors.
8. No stale report for a different analysis context.
9. No green progress stage without persisted backend artifact.
10. No Offer / Content / Publication without valid upstream state.

**Cursor must not write:** `COMPLETE`, `accepted`, `frozen`, `commercially ready` without owner.

---

## Execution order (single queue)

| Step | Program | Exit criterion |
|------|---------|----------------|
| **A** | [01.3B.2A](./PRODUCT-01.3B.2A-OWNER-SMOKE.md) Research value | Owner sees partial research output, not error log — **owner PASS** |
| **B** | [PRODUCT-QA-01](./PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md) | Golden scenario + contract + Playwright + owner gate |
| **C** | PRODUCT-01.3C Verdict & Confidence Integrity | Honest verdict types; factor breakdown, not decorative % |
| **D** | PRODUCT-01.3D Honest Report & Progress | Stage = artifact exists; reload restores same run |
| **E** | PRODUCT-01.3E Full Owner Acceptance | idea → research → verdict → offer → reload — **owner PASS** |
| **F** | **Freeze PRODUCT-01** | BIV + verdict + offer path locked |
| **G** | [PRODUCT-02](./PRODUCT-02-TELEGRAM-PUBLICATION-GOLDEN-PATH.md) | Offer → Telegram draft → approve → publish → message_id |
| **H** | Full commercial E2E | End-to-end golden path green |
| **I** | **Freeze commercial MVP** | Sellable v1 |
| **J** | Media / Higgsfield (optional) | [LEGACY Visual Golden Path](./PRODUCT-03-VISUAL-ASSET-GOLDEN-PATH.md) (historical ID PRODUCT-03; **not** Strategy Architecture) — after Telegram text path |

**Stop opening unrelated phases.** Report progress against golden path steps, not file counts.

---

## Current focus (now)

```
Research quality (01.3B.2A owner smoke)
  → QA harness (PRODUCT-QA-01)
  → Verdict (01.3C)
  → Offer (existing, re-accept after 01.3E)
  → Telegram post + publish (PRODUCT-02)
```

Everything else **frozen**.

---

## Verdict types (01.3C target)

- `proceed`
- `proceed_with_conditions`
- `revise`
- `defer`
- `stop`
- `insufficient_evidence`

Confidence UI = factor breakdown (source quality, market coverage, competitors, audience, pricing, critical gaps) — **not** single decorative percentage.

---

## Progress honesty (01.3D target)

```
research track completed
  → evidence persisted
  → finding formed
  → stage marked done
```

Not: «request sent → stage done».

---

## Related docs

- [PRODUCT-TRACK-PRIORITY-PLAN.md](./PRODUCT-TRACK-PRIORITY-PLAN.md) — priority index (points here)
- [PRODUCT-01.3B.2A-OWNER-SMOKE.md](./PRODUCT-01.3B.2A-OWNER-SMOKE.md) — binding owner smoke
- [PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md](./PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md)
- CWF.1 boundary: `.cursor/rules/commercial-product-directive.mdc`

---

## Anti-patterns (do not repeat)

- Pytest green → mark complete → browser FAIL
- Another presentation slice without research value
- New MCP / platform work before golden path
- «Fully working» = all modules sketched vs one path finished

**v1 = one finished well, not twenty started.**

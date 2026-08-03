# Skill Audit — Landing Copywriting

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-009` |
| **Marketsynth ID** | `MS-SKILL-011` |
| **Candidate name** | Landing Copywriting |
| **Source URL / repo** | https://github.com/coreyhaines31/marketingskills/tree/main/skills/copywriting |
| **Author / vendor** | Corey Haines |
| **License** | MIT |
| **Version reviewed** | Not verified |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Write or improve marketing copy for landing/home/pricing pages using research-informed language.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Launch Pack → Content Assets |
| User-visible result | Directly feeds 3 Content Assets step in CWF.1. |
| Willingness-to-pay hypothesis | Strengthens sellable workflow when output feeds Evidence → Verdict → Launch Pack without parallel tooling UI |
| Fits single golden path? | partial — methodology must map to internal subskills, not a standalone agent surface |
| Parallel workflow risk? | low if internalized; high if installed as external drop-in marketplace Skill |

---

## 3. Problem solved

### User problem

Write or improve marketing copy for landing/home/pricing pages using research-informed language.

### Marketsynth workflow stage

Launch Pack → Content Assets

### Expected commercial value

Directly feeds 3 Content Assets step in CWF.1.

---

## 4. Methodology

Page-type playbooks, research-informed copy, ties to product-marketing context and customer-research VOC.

### Required inputs

- Page type
- Product context
- VOC quotes

### Expected outputs

- Draft copy blocks
- Headline variants

### Known assumptions

- Requires governed product context (Marketsynth project/brief), not a local `.agents/` file.
- External Skill assumes agent workspace file I/O; Marketsynth must replace with persisted contracts + Evidence.

---

## 5. Capability description

### Dependencies

- MS-SKILL-001/002 outputs

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | partial — frameworks help structure research; LLM synthesis still needs Source/Evidence gates |
| Honest about limits | yes in source Skill (confidence labels, sample bias warnings where present) |
| Suitable without mock in production | no as drop-in; yes after Adapt to internal operator |

---

## 6. Architecture fit

Content asset generation subskill with approval before publish.

| Check | Requirement |
|-------|-------------|
| Evidence contract | Map outputs to Citation Contract (Answer + Evidence + Source + Confidence) |
| Approval boundary | Human approval before customer-facing launch/publish/spend |
| Tenant isolation | Skill context scoped per project/tenant, not shared filesystem |
| Runtime | Internal subskill under `app/specialist_skills/` / domain operators — not external SKILL.md mount |

---

## 7. Security and trust

Low; output is text.

| Check | Result | Notes |
|-------|--------|-------|
| Prompt injection surface | medium | Ingested web/review content must pass sanitize + evidence labeling |
| Secret handling | safe if no external scripts executed | Reject bundled shell/network scripts in production path |
| Network egress scope | bounded when wired through approved research tools only | |
| Write side effects | none in methodology-only Adapt path | |
| PII / tenant isolation | pass after Adapt | |
| Supply chain risk | medium | Third-party markdown + optional scripts — methodology reuse only |

---

## 8. Quality

Depends on input evidence quality.

---

## 9. Legal

MIT

### Reuse decision split

Methodology Adapt.

| Reuse type | Decision |
|------------|----------|
| A. Methodology reuse | Adapt |
| B. Package structure reuse | Adapt (align to Agent Skills spec + Marketsynth contracts) |
| C. Direct code reuse | Reject in SKILL-R0.1 |
| D. Direct production installation | Reject |

---

## 10. Comparison to Marketsynth today

| Dimension | External Skill | Current internal approach |
|-----------|----------------|---------------------------|
| Registry location | External repo folder | `app/specialist_skills/` |
| Execution path | Agent auto-activation | Explicit specialist / operator runs |
| Evidence contract | Informal markdown outputs | Citation Contract + research runs |
| Human approval | Not enforced | CWF gates (verdict, launch, publish) |

---

## 11. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 2 | |
| Golden path fit | 2 | |
| Evidence integrity | 1 | |
| Security / trust | 2 | |
| Implementation cost | 1 | |
| Maintenance burden | 1 | |
| Duplicate of existing | 1 | |

**Total:** 10 / 14

---

## 12. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | Needed for content factory slice; must use governed context not `.agents/` files. |
| **Required modifications** | - Template to Content Asset contracts
- Approval gate before Telegram publish path |
| **Defer unblock condition** | After content asset slice scoped |
| **Owner sign-off** | pending |
| **RFC required** | Yes — RFC-SKILL-002 after CWF slice need |

---

## 13. Implementation gate

| Gate | Allowed? |
|------|----------|
| SKILL-R0 / R0.1 research only | ✅ |
| RFC-SKILL-001..003 draft | after owner accepts Adapt decision |
| Production Skill code | after RFC + CWF slice + owner browser acceptance |

---

## Sources

- marketingskills/skills/copywriting/

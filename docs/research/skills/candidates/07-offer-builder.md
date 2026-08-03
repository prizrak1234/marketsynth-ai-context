# Skill Audit — Offer Builder

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-007` |
| **Marketsynth ID** | `MS-SKILL-007` |
| **Candidate name** | Offer Builder |
| **Source URL / repo** | https://github.com/coreyhaines31/marketingskills/tree/main/skills/offers (+ pricing cross-ref) |
| **Author / vendor** | Corey Haines |
| **License** | MIT |
| **Version reviewed** | 1.0.0 |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Design complete commercial offer (deliverable, bonuses, guarantee, urgency, naming, payment structure) beyond page copy.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Verdict → Launch Pack / Offer |
| User-visible result | Supports sellable Launch Pack and paid workflow after positive/conditional verdict. |
| Willingness-to-pay hypothesis | Strengthens sellable workflow when output feeds Evidence → Verdict → Launch Pack without parallel tooling UI |
| Fits single golden path? | partial — methodology must map to internal subskills, not a standalone agent surface |
| Parallel workflow risk? | low if internalized; high if installed as external drop-in marketplace Skill |

---

## 3. Problem solved

### User problem

Design complete commercial offer (deliverable, bonuses, guarantee, urgency, naming, payment structure) beyond page copy.

### Marketsynth workflow stage

Verdict → Launch Pack / Offer

### Expected commercial value

Supports sellable Launch Pack and paid workflow after positive/conditional verdict.

---

## 4. Methodology

Value Equation (Hormozi frame), six-component offer anatomy, diagnostic loop, banned vocabulary list, type-specific playbooks in references/.

### Required inputs

- Product context
- Pricing constraints
- Proof points
- Verdict/segment context

### Expected outputs

- Offer blueprint
- Component-level recommendations
- Risk/reverse notes

### Known assumptions

- Requires governed product context (Marketsynth project/brief), not a local `.agents/` file.
- External Skill assumes agent workspace file I/O; Marketsynth must replace with persisted contracts + Evidence.

---

## 5. Capability description

### Dependencies

- MS-SKILL-006 positioning
- Optional pricing skill for SaaS tiers

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | partial — frameworks help structure research; LLM synthesis still needs Source/Evidence gates |
| Honest about limits | yes in source Skill (confidence labels, sample bias warnings where present) |
| Suitable without mock in production | no as drop-in; yes after Adapt to internal operator |

---

## 6. Architecture fit

Launch Pack scope input — must not auto-publish or auto-price without approval.

| Check | Requirement |
|-------|-------------|
| Evidence contract | Map outputs to Citation Contract (Answer + Evidence + Source + Confidence) |
| Approval boundary | Human approval before customer-facing launch/publish/spend |
| Tenant isolation | Skill context scoped per project/tenant, not shared filesystem |
| Runtime | Internal subskill under `app/specialist_skills/` / domain operators — not external SKILL.md mount |

---

## 7. Security and trust

Low technical risk; commercial risk if guarantees over-promised — gate with human approval.

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

Reference library + diagnostic loop; eval coverage **Not verified** for offers skill.

---

## 9. Legal

MIT; Hormozi framework attribution in source — no legal issue for internal Adapt.

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
| **Rationale** | High value for Launch Pack, but offer construction must respect Marketsynth commercial gates and not bypass pricing/approval. |
| **Required modifications** | - Map offer blueprint to LaunchPackRequest fields
- Forbid manipulative scarcity patterns in product copy templates
- Separate offer design from execution/publish |
| **Defer unblock condition** | N/A |
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

- https://raw.githubusercontent.com/coreyhaines31/marketingskills/main/skills/offers/SKILL.md
- offers/references/*.md (structure reference)

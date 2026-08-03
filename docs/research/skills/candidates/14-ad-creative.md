# Skill Audit — Ad Creative

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-014` |
| **Marketsynth ID** | `MS-SKILL-016` |
| **Candidate name** | Ad Creative |
| **Source URL / repo** | https://github.com/coreyhaines31/marketingskills/tree/main/skills/ad-creative + skills/ads |
| **Author / vendor** | Corey Haines |
| **License** | MIT |
| **Version reviewed** | Not verified |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Generate and iterate paid ad creative (headlines, primary text, variants).

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Launch Pack (paid acquisition optional) |
| User-visible result | Optional post-launch — not required for first CWF.1 paying slice. |
| Willingness-to-pay hypothesis | Strengthens sellable workflow when output feeds Evidence → Verdict → Launch Pack without parallel tooling UI |
| Fits single golden path? | partial — methodology must map to internal subskills, not a standalone agent surface |
| Parallel workflow risk? | low if internalized; high if installed as external drop-in marketplace Skill |

---

## 3. Problem solved

### User problem

Generate and iterate paid ad creative (headlines, primary text, variants).

### Marketsynth workflow stage

Launch Pack (paid acquisition optional)

### Expected commercial value

Optional post-launch — not required for first CWF.1 paying slice.

---

## 4. Methodology

Creative iteration frameworks; ads skill for campaign structure.

### Required inputs

- Offer/positioning
- Platform constraints

### Expected outputs

- Ad creative variants

### Known assumptions

- Requires governed product context (Marketsynth project/brief), not a local `.agents/` file.
- External Skill assumes agent workspace file I/O; Marketsynth must replace with persisted contracts + Evidence.

---

## 5. Capability description

### Dependencies

- Ad platform MCPs **Defer** (Google/Meta/Yandex cards)

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | partial — frameworks help structure research; LLM synthesis still needs Source/Evidence gates |
| Honest about limits | yes in source Skill (confidence labels, sample bias warnings where present) |
| Suitable without mock in production | no as drop-in; yes after Adapt to internal operator |

---

## 6. Architecture fit

Draft-only until ad connector RFC approved.

| Check | Requirement |
|-------|-------------|
| Evidence contract | Map outputs to Citation Contract (Answer + Evidence + Source + Confidence) |
| Approval boundary | Human approval before customer-facing launch/publish/spend |
| Tenant isolation | Skill context scoped per project/tenant, not shared filesystem |
| Runtime | Internal subskill under `app/specialist_skills/` / domain operators — not external SKILL.md mount |

---

## 7. Security and trust

Medium if wired to live ad APIs — writes must be gated.

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

Variant generation — human review required.

---

## 9. Legal

MIT

### Reuse decision split

Methodology Adapt later.

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
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 1 | |
| Security / trust | 0 | |
| Implementation cost | 1 | |
| Maintenance burden | 1 | |
| Duplicate of existing | 1 | |

**Total:** 6 / 14

---

## 12. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Creative skill useful, but live ad MCP connectors not audited/approved; avoid spend surface. |
| **Required modifications** | - Draft-only mode first |
| **Defer unblock condition** | After ad MCP RFC + budget gateway |
| **Owner sign-off** | pending |
| **RFC required** | No |

---

## 13. Implementation gate

| Gate | Allowed? |
|------|----------|
| SKILL-R0 / R0.1 research only | ✅ |
| RFC-SKILL-001..003 draft | after owner accepts Adapt decision |
| Production Skill code | after RFC + CWF slice + owner browser acceptance |

---

## Sources

- marketingskills/skills/ad-creative/
- marketingskills/skills/ads/

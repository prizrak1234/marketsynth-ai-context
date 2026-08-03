# Skill Audit — Market Research

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-002` |
| **Marketsynth ID** | `MS-SKILL-002` |
| **Candidate name** | Market Research |
| **Source URL / repo** | https://github.com/coreyhaines31/marketingskills/tree/main/skills/customer-research (Mode 2 + synthesis) |
| **Author / vendor** | Corey Haines |
| **License** | MIT |
| **Version reviewed** | 2.0.1 |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Structured customer and market research synthesis from interviews, reviews, communities, and surveys — with confidence labeling.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Research / Evidence |
| User-visible result | Directly strengthens CWF.1 Research → Evidence by producing theme clusters and citeable quotes for verdict inputs. |
| Willingness-to-pay hypothesis | Strengthens sellable workflow when output feeds Evidence → Verdict → Launch Pack without parallel tooling UI |
| Fits single golden path? | partial — methodology must map to internal subskills, not a standalone agent surface |
| Parallel workflow risk? | low if internalized; high if installed as external drop-in marketplace Skill |

---

## 3. Problem solved

### User problem

Structured customer and market research synthesis from interviews, reviews, communities, and surveys — with confidence labeling.

### Marketsynth workflow stage

Research / Evidence

### Expected commercial value

Directly strengthens CWF.1 Research → Evidence by producing theme clusters and citeable quotes for verdict inputs.

---

## 4. Methodology

Dual mode: (1) analyze existing assets, (2) digital watering hole research. Frameworks: JTBD extraction, confidence table (High/Med/Low), persona structure, synthesis template. Requires product-marketing context first.

### Required inputs

- Research goal
- Existing transcripts/reviews/tickets (optional)
- ICP hints
- Approved research sources

### Expected outputs

- Research synthesis report
- VOC quote bank
- Persona drafts (≥5 data points/segment)
- Research gap analysis

### Known assumptions

- Requires governed product context (Marketsynth project/brief), not a local `.agents/` file.
- External Skill assumes agent workspace file I/O; Marketsynth must replace with persisted contracts + Evidence.

---

## 5. Capability description

### Dependencies

- Tools: web/review access via **governed** research connectors (XmlRiver/Firecrawl), not ad-hoc browsing
- Knowledge: product context
- External APIs: review platforms — not auto-wired

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | partial — frameworks help structure research; LLM synthesis still needs Source/Evidence gates |
| Honest about limits | yes in source Skill (confidence labels, sample bias warnings where present) |
| Suitable without mock in production | no as drop-in; yes after Adapt to internal operator |

---

## 6. Architecture fit

Maps to `research.web_source_collection` + BIV evidence hydration. Evidence: every theme links to Source candidates → Evidence admission. Approval: human review before verdict weighting.

| Check | Requirement |
|-------|-------------|
| Evidence contract | Map outputs to Citation Contract (Answer + Evidence + Source + Confidence) |
| Approval boundary | Human approval before customer-facing launch/publish/spend |
| Tenant isolation | Skill context scoped per project/tenant, not shared filesystem |
| Runtime | Internal subskill under `app/specialist_skills/` / domain operators — not external SKILL.md mount |

---

## 7. Security and trust

Network access required for Mode 2 — must route through Connector Gateway. Prompt injection: **high** on scraped UGC. No shell in core skill.

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

Confidence labeling built-in. Eval coverage claimed at repo level — **Requires technical validation** for this specific skill mapping. Hallucination risk if sample size ignored.

---

## 9. Legal

MIT

### Reuse decision split

Methodology: Adapt. Direct skill folder: Reject for production.

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
| Evidence integrity | 2 | |
| Security / trust | 1 | |
| Implementation cost | 1 | |
| Maintenance burden | 1 | |
| Duplicate of existing | 0 | |

**Total:** 9 / 14

---

## 12. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | Strong methodology overlap with Marketsynth research operators; must not bypass Source→Evidence admission or tenant research budgets. |
| **Required modifications** | - Split Mode 2 web mining into audited connector calls
- Enforce minimum sample + recency rules in operator code
- Output JSON schema for themes/quotes with source IDs |
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

- https://github.com/coreyhaines31/marketingskills/tree/main/skills/customer-research
- https://raw.githubusercontent.com/coreyhaines31/marketingskills/main/skills/customer-research/SKILL.md
- Marketsynth `app/research_source_collection/` (internal baseline)

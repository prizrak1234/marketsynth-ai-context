# Skill Audit — Product Marketing Context

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-001` |
| **Marketsynth ID** | `MS-SKILL-001` |
| **Candidate name** | Product Marketing Context |
| **Source URL / repo** | https://github.com/coreyhaines31/marketingskills/tree/main/skills/product-marketing |
| **Author / vendor** | Corey Haines |
| **License** | MIT (repo root LICENSE verified 2026-07-23) |
| **Version reviewed** | 2.1.0 (SKILL.md metadata) |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Captures durable product, audience, positioning, voice, and proof context so downstream marketing work does not re-ask foundations.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Idea / Research (foundational context before verdict inputs) |
| User-visible result | Reduces time-to-first Launch Pack by reusing governed project context across research, offer, and content steps. |
| Willingness-to-pay hypothesis | Strengthens sellable workflow when output feeds Evidence → Verdict → Launch Pack without parallel tooling UI |
| Fits single golden path? | partial — methodology must map to internal subskills, not a standalone agent surface |
| Parallel workflow risk? | low if internalized; high if installed as external drop-in marketplace Skill |

---

## 3. Problem solved

### User problem

Captures durable product, audience, positioning, voice, and proof context so downstream marketing work does not re-ask foundations.

### Marketsynth workflow stage

Idea / Research (foundational context before verdict inputs)

### Expected commercial value

Reduces time-to-first Launch Pack by reusing governed project context across research, offer, and content steps.

---

## 4. Methodology

Framework: 12-section product marketing context doc (overview, ICP, personas, pains, competition, differentiation, objections, switching dynamics, customer language, brand voice, proof, goals) with versioning/changelog. Activation: read-or-create `.agents/product-marketing.md`; optional auto-draft from codebase.

### Required inputs

- Business/product description
- Existing site/copy/docs
- Customer quotes (optional)
- Competitive notes

### Expected outputs

- Structured product marketing context document
- Changelog/version trail

### Known assumptions

- Requires governed product context (Marketsynth project/brief), not a local `.agents/` file.
- External Skill assumes agent workspace file I/O; Marketsynth must replace with persisted contracts + Evidence.

---

## 5. Capability description

### Dependencies

- Tools: file read (external); Marketsynth: project brief + knowledge snapshots
- Knowledge: prior BIV/research outputs
- External APIs: none required

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | partial — frameworks help structure research; LLM synthesis still needs Source/Evidence gates |
| Honest about limits | yes in source Skill (confidence labels, sample bias warnings where present) |
| Suitable without mock in production | no as drop-in; yes after Adapt to internal operator |

---

## 6. Architecture fit

Compatible CWF.1 steps: Idea → Research. Maps to persisted **Project Marketing Context** entity (not workspace `.agents/`). Evidence: context fields must cite sources where factual. Approval: owner confirms context before verdict-affecting use.

| Check | Requirement |
|-------|-------------|
| Evidence contract | Map outputs to Citation Contract (Answer + Evidence + Source + Confidence) |
| Approval boundary | Human approval before customer-facing launch/publish/spend |
| Tenant isolation | Skill context scoped per project/tenant, not shared filesystem |
| Runtime | Internal subskill under `app/specialist_skills/` / domain operators — not external SKILL.md mount |

---

## 7. Security and trust

External scripts: none in core SKILL.md. Shell commands: none required for methodology. Network: optional codebase read. Prompt injection: medium via ingested marketing copy. Tool poisoning: low if markdown-only Adapt.

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

Repo claims eval/test infrastructure (see marketingskills README / releases). Deterministic checks: partial (section completeness). Output schema: informal markdown template. Failure modes: invented ICP details if auto-draft unchecked. Hallucination risk: medium without Evidence gates.

---

## 9. Legal

MIT — modification and redistribution allowed with attribution. No separate trademark grant verified.

### Reuse decision split

Methodology and section taxonomy: **Adapt**. Package structure (SKILL.md + references): **Adapt** per agentskills.io. Direct install: **Reject**.

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
| Security / trust | 1 | |
| Implementation cost | 1 | |
| Maintenance burden | 1 | |
| Duplicate of existing | 1 | |

**Total:** 9 / 14

---

## 12. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | High P0 commercial value as **internal governed context layer**, but external file-based activation conflicts with Marketsynth tenant storage, Evidence, and CWF gates. Do not install drop-in. |
| **Required modifications** | - Persist as tenant-scoped contract + DB/knowledge artifact
- Wire to BIV and Launch Pack inputs
- Remove `.agents/` filesystem assumption
- Require source citations for factual claims
- Human confirmation gate before verdict consumption |
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

- https://github.com/coreyhaines31/marketingskills/tree/main/skills/product-marketing
- https://raw.githubusercontent.com/coreyhaines31/marketingskills/main/skills/product-marketing/SKILL.md
- https://github.com/coreyhaines31/marketingskills/blob/main/LICENSE
- https://agentskills.io/specification

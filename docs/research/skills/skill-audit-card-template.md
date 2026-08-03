# Skill Audit Card — Template

> Copy this file to `docs/research/skills/candidates/<slug>.md` and fill every section.  
> Delete instructional lines marked `(instruction)` before marking **Ready for review**.

---

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `SKILL-AUDIT-____` |
| **Candidate name** | |
| **Source URL / repo** | |
| **Author / vendor** | |
| **License** | |
| **Version reviewed** | |
| **Reviewed by** | |
| **Review date** | YYYY-MM-DD |
| **Status** | draft \| ready_for_review \| decided |

---

## 1. One-line summary

(instruction) What user problem does this Skill claim to solve?

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened (if any) | Idea / Research / Verdict / Launch Pack / Content / Publish / none |
| User-visible result | |
| Willingness-to-pay hypothesis | |
| Fits single golden path? | yes / no / partial |
| Parallel workflow risk? | none / low / high |

(instruction) Reject or Defer if it creates a second product surface or bypasses evidence/approval.

---

## 3. Capability description

### Inputs

- 

### Outputs

- 

### Dependencies

- Tools:
- Knowledge:
- External APIs:

### Determinism / evidence

| Criterion | Assessment |
|-----------|------------|
| Produces citeable evidence | yes / no / partial |
| Honest about limits | yes / no / unknown |
| Suitable without mock in production | yes / no |

---

## 4. Security and trust

| Check | Result | Notes |
|-------|--------|-------|
| Prompt injection surface | low / medium / high | |
| Secret handling | safe / unsafe / unknown | |
| Network egress scope | bounded / unbounded | |
| Write side effects | none / gated / uncontrolled | |
| PII / tenant isolation | pass / fail / unknown | |
| Supply chain risk | low / medium / high | |

(instruction) Any **uncontrolled write** or **unbounded egress** → default **Reject** unless RFC-SKILL-003 exception.

---

## 5. Comparison to Marketsynth today

| Dimension | External Skill | Current internal approach |
|-----------|----------------|---------------------------|
| Registry location | | `app/specialist_skills/` |
| Execution path | | explicit run / subskill |
| Evidence contract | | Citation Contract |
| Human approval | | CWF gates |

---

## 6. Adopt / Adapt / Reject scoring

Use [Adopt-Adapt-Reject Matrix](../adopt-adapt-reject-matrix.md).

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | | |
| Golden path fit | | |
| Evidence integrity | | |
| Security / trust | | |
| Implementation cost | | |
| Maintenance burden | | |
| Duplicate of existing | | |

**Total:** ___ / 12

---

## 7. Decision

| Decision | ☐ Adopt ☐ Adapt ☐ Reject ☐ Defer |
|----------|-----------------------------------|
| **Rationale** | |
| **If Adapt — required changes** | e.g. internal subskill only; contracts first; no marketplace UI |
| **If Defer — unblock condition** | e.g. after CWF.1e Telegram publish accepted |
| **Owner sign-off** | pending / approved / rejected |
| **Date decided** | |

---

## 8. Implementation gate (do not fill until post-RFC)

| Gate | Allowed? |
|------|----------|
| SKILL-R0 research only | ✅ always |
| RFC-SKILL-001..003 draft | after decision Adopt/Adapt |
| SKILL-01 code | after RFC acceptance |
| SKILL-04 production Skill | after CWF slice + owner browser acceptance |

---

## 9. Evidence appendix

(instruction) Paste minimal reproducible examples, screenshots, or links. No secrets.

- 

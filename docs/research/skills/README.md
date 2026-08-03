# Skill Research — audit workspace

**Phase:** SKILL-R0  
**Scope:** research and architecture input only — **not** executable Skills.

---

## What belongs here

- Completed **Skill audit cards** (one file per candidate)
- Notes from owner review
- Links to source repos, licenses, and security disclosures
- Draft inputs for RFC-SKILL-001..003

## What does NOT belong here

- Runtime skill packages wired into `app/specialist_skills/` or CWF
- Prompt dumps without audit metadata
- Marketplace catalogs copied wholesale without per-skill decisions

---

## How to add a candidate

1. Copy [skill-audit-card-template.md](skill-audit-card-template.md) to  
   `docs/research/skills/candidates/<slug>.md`
2. Fill all required sections.
3. Score using [../adopt-adapt-reject-matrix.md](../adopt-adapt-reject-matrix.md).
4. Set decision: **Adopt | Adapt | Reject | Defer**.
5. If Adopt/Adapt — add to RFC draft queue in research README; do **not** implement.

---

## Naming convention

```
candidates/<vendor-or-author>-<skill-name>.md
```

Examples:

- `candidates/openai-deep-research-audit.md`
- `candidates/internal-audience-segmentation-subskill.md`

---

## Reference (existing product)

- [../../skill_registry.md](../../skill_registry.md) — current H2.2 internal registry
- [../../specialist_capability_packs.md](../../specialist_capability_packs.md)
- [../../user_request_skill_context.md](../../user_request_skill_context.md)
- CWF.1 internal subskills (e.g. Audience Segmentation inside Business Idea Validator) = **Adapt** pattern, not user-facing marketplace Skills

---

## RFC outputs (future)

Research cards feed:

- **RFC-SKILL-001** — Skill Registry Specification
- **RFC-SKILL-002** — Skill Package Format
- **RFC-SKILL-003** — Skill Security and Trust Boundary

Do not draft RFCs until at least **5 audited candidates** exist or owner requests early RFC kickoff.

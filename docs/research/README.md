# Research Foundation — SKILL-R0

**Phase:** SKILL-R0 (Research Foundation) · **SKILL-R0.1 Candidate Audit Pack complete**  
**Status:** active — research only  
**Product track frozen:** CWF.1 (no runtime changes from this phase)

---

## Purpose

Prepare a **safe audit base** for evaluating external Skills and MCP connectors **before** any registry, runtime, or production integration work.

This phase produces **documentation and templates only**. It does not:

- change production runtime;
- add third-party Skills to the executable contour;
- connect new external MCP servers;
- modify CWF.1 product logic or UI.

---

## Directories

| Path | Contents |
|------|----------|
| [skills/](skills/) | Skill audit cards, evaluation criteria, future RFC-SKILL inputs |
| [mcp/](mcp/) | MCP / connector audit cards, trust boundary notes, future RFC-CONN inputs |

Shared decision tool: [adopt-adapt-reject-matrix.md](adopt-adapt-reject-matrix.md)

**SKILL-R0.1 outputs:** [SKILL-R0.1-candidate-audit-summary.md](SKILL-R0.1-candidate-audit-summary.md) · 16 skill cards · 16 MCP cards · [browser comparison](mcp/browser-research-comparison.md) · [ecosystem comparison](skills/source-ecosystem-comparison.md)

---

## Research workflow

```
Candidate discovered
→ fill audit card (Skill or MCP)
→ score against adopt-adapt-reject matrix
→ owner review
→ decision recorded in card
→ only Adopt/Adapt candidates enter RFC draft queue
```

**No candidate becomes executable** until explicit owner approval of a later implementation phase.

---

## Downstream deliverables (after research — not part of R0)

| RFC | Title | Phase |
|-----|-------|-------|
| RFC-SKILL-001 | Skill Registry Specification | pre SKILL-01 |
| RFC-SKILL-002 | Skill Package Format | pre SKILL-01 |
| RFC-SKILL-003 | Skill Security and Trust Boundary | pre SKILL-01 |
| RFC-CONN-001 | Connector / MCP Registry | pre SKILL-01 |

---

## Implementation phases (deferred)

| Phase | Scope | Gate |
|-------|-------|------|
| **SKILL-01** | Foundation implementation | RFC-SKILL-001..003 accepted |
| **SKILL-02** | Runtime integration | SKILL-01 + security sign-off |
| **SKILL-03** | Evidence and approval integration | CWF golden path alignment |
| **SKILL-04** | First production Skills | Owner browser acceptance |

---

## Relationship to existing product

| Existing | Role during R0 |
|----------|----------------|
| CWF.1 golden path | **Frozen** — research must not fork parallel workflows |
| `app/specialist_skills/` | Current internal skill registry — reference only |
| `app/mcp/` | Current read-only Search/Fetch MCP — reference only |
| CMVP.1 Business Idea Validator | Example of **internal subskill** pattern (Adapt, not marketplace Skill) |

---

## Cursor rules for this track

1. Classify every research task as **D (post-pilot enhancement)** or **E (technical curiosity)** unless it directly unblocks CWF revenue path.
2. SKILL-R0 tasks are allowed as **research documentation only**.
3. Do not implement SKILL-01+ until owner closes research selection and RFCs are accepted.
4. Every audit card must state **commercial fit**: which CWF step (if any) it strengthens.

---

## Owner acceptance (SKILL-R0)

SKILL-R0 is complete when:

- [ ] `docs/research/skills/` exists with audit template
- [ ] `docs/research/mcp/` exists with audit template
- [ ] adopt-adapt-reject matrix is published
- [ ] no production code, migrations, or API changes in the same PR
- [ ] owner confirms research can begin without product regression risk

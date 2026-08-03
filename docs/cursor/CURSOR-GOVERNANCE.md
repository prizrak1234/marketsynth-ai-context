# Cursor Development Governance

**Task:** CURSOR-GOVERNANCE-01  
**Purpose:** Reproducible planning, independent review, and evidence-based PASS/FAIL for Cursor work on Marketsynth.  
**Not a product program** — does not change runtime priority (see `knowledge/06_CURRENT_STATE.md`).

## Workflow

```
Owner-approved task
  → Planning Gate (rule: marketsynth-planning-gate)
  → Implementation
  → Parallel Review (5 read-only subagents)
  → Verification (tests/commands)
  → Composite Verdict (skill: marketsynth-composite-review)
  → Delivery Report (rule: marketsynth-delivery-report)
  → SoT update (when product slice warrants)
```

## Components

| Component | Path |
|-----------|------|
| Planning Gate | `.cursor/rules/marketsynth-planning-gate.mdc` |
| Delivery Report | `.cursor/rules/marketsynth-delivery-report.mdc` |
| Architecture reviewer | `.cursor/agents/marketsynth-architecture-reviewer.md` |
| Product reviewer | `.cursor/agents/marketsynth-product-reviewer.md` |
| Security reviewer | `.cursor/agents/marketsynth-security-reviewer.md` |
| Runtime reviewer | `.cursor/agents/marketsynth-runtime-reviewer.md` |
| Test reviewer | `.cursor/agents/marketsynth-test-reviewer.md` |
| Composite review | `.cursor/skills/marketsynth-composite-review/SKILL.md` |
| Hooks | `.cursor/hooks.json` (prompt-based reminders/guards) |
| Dry-run scenarios | `.cursor/governance/dry-run-scenarios.md` |

## When to run composite review

**Run:** non-trivial product/runtime code changes; before claiming PASS on slices.  
**Skip:** read-only audits, typo-only, governance-only edits.

## Superpowers plugin

**Decision: do not install in this task.**

- Official install: Cursor Agent chat `/add-plugin superpowers` (marketplace)
- Risk: plugin hooks/skills may alter workflow vs SoT; version not pinned in repo
- **Owner action:** trial in a branch; verify plugin detection; pin/rollback before team adoption
- **Substitute:** `marketsynth-planning-gate` + `marketsynth-composite-review` (native rules/skills/subagents)

Borrow **ideas** from Superpowers (planning checklist, TDD emphasis) via our rules — do not copy the full framework.

## Rollback

Delete added paths:

```text
.cursor/rules/marketsynth-planning-gate.mdc
.cursor/rules/marketsynth-delivery-report.mdc
.cursor/agents/marketsynth-*-reviewer.md
.cursor/skills/marketsynth-composite-review/
.cursor/hooks.json
.cursor/governance/
docs/cursor/CURSOR-GOVERNANCE.md
```

Revert any one-line pointer added to `AGENTS.md` if desired. No product code to revert.

## Conflicts

- **AGENTS.md** — top-level operational contract for assistants
- **commercial-product-directive** — product slice quality (unchanged)
- **botfazer-foundation** — code structure (unchanged)
- Governance rules add process; they do not override owner-approved Task IDs

## Verification (owner)

1. Open Cursor → confirm Project Rules list includes planning + delivery report rules
2. Confirm `.cursor/agents/` shows five reviewers (Settings / agent list)
3. New Agent session → sessionStart hook should remind about Planning Gate
4. Run dry-run scenarios in `.cursor/governance/dry-run-scenarios.md`

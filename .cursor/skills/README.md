# Marketsynth Cursor Skills (project)

> **Layer:** Cursor Development Governance — not product capabilities.  
> **Rule:** Skills = procedures. Invariants stay in `.cursor/rules/` and `AGENTS.md`.  
> **PASS** still requires tests / commands / API / browser / owner evidence — never skill alone.

## Stage 1 (active)

| Skill | Purpose |
|-------|---------|
| [marketsynth-cold-start](./marketsynth-cold-start/SKILL.md) | Restore execution point from SoT; no code |
| [marketsynth-task-preflight](./marketsynth-task-preflight/SKILL.md) | Pre-implementation gate before product/runtime edits |
| [marketsynth-cursor-tz](./marketsynth-cursor-tz/SKILL.md) | Fixed-contract Task ID / ТЗ drafts |

## Already present

| Skill | Purpose |
|-------|---------|
| [marketsynth-composite-review](./marketsynth-composite-review/SKILL.md) | 5-reviewer composite gate (Stage 2 precursor) |

## Stage 2 (planned — do not invent early)

- `marketsynth-review-gate` (formalize composite + evidence bans)
- `marketsynth-owner-report`
- `marketsynth-sot-session-close` (+ optional `scripts/validate_sot_consistency.py`)

## Stage 3 (after 2026-08-18 — Research Hardening window)

- `marketsynth-evidence-audit`
- `marketsynth-xmlriver-diagnostics` (**dev diagnostics only**)

**Product boundary:** XMLRiver / Wordstat in commercial Research = provider **adapter** inside Research Pipeline — not LLM-run skill scripts with API keys.

## Do not

- Mass-install skills.sh packages without audit
- Move always-on invariants into skills
- Store API keys in skill folders
- Treat skills as Marketsynth product capabilities or Golden Path steps
- Grant third-party skills write access to SoT

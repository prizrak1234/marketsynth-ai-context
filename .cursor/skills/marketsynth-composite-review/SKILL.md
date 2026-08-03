---
name: marketsynth-composite-review
description: Runs five independent read-only Marketsynth reviewer subagents on an implementation diff and produces a composite PASS/FAIL/INCONCLUSIVE verdict. Use after non-trivial code changes before claiming PASS on product or runtime work.
disable-model-invocation: true
---

# Marketsynth Composite Review

Orchestrates **five independent read-only reviews**. Reviewers do not fix code.

## When to run

- After implementation with changes to `app/`, `web/`, `tests/`
- Before owner PASS on product slices
- On critical audit tasks when owner requests review

**Skip** for: read-only Q&A, governance-only edits, trivial typos.

## Inputs required

1. **Task ID** and approved scope (one paragraph)
2. **Diff** — prefer `git diff` / branch diff; else explicit change description per file
3. **Changed files list**
4. **Verification results** — tests actually run + outcomes

## Procedure

1. Confirm diff and scope — if diff missing, verdict **INCONCLUSIVE**
2. Launch **five reviewers in parallel** — each isolated, no shared thread:
   - `marketsynth-architecture-reviewer`
   - `marketsynth-product-reviewer`
   - `marketsynth-security-reviewer`
   - `marketsynth-runtime-reviewer`
   - `marketsynth-test-reviewer`

3. For each launch:
   - Invoke the matching agent from `.cursor/agents/marketsynth-*-reviewer.md`
   - Pass: diff, changed files, task scope, verification output
   - **Do not** pass other reviewers' conclusions into the prompt
   - Require strict output format from agent file

4. Aggregate into composite verdict (below)
5. **Do not auto-fix** blocking findings — return to implementation, then re-run this skill

## Composite verdict rules

| Verdict | Condition |
|---------|-----------|
| **FAIL** | Any blocking finding; required test command failed; scope expansion; security high/critical applicable issue; critical subsystem unreviewable |
| **INCONCLUSIVE** | Missing diff/files; verification not run; environment blocked proof; reviewers materially disagree on facts |
| **PASS** | All five reviewers completed; zero blocking findings; required tests green; scope honored; claims match evidence |

Built-in **security-review** / **bugbot** subagents may supplement but **do not replace** marketsynth-security-reviewer or other custom reviewers for composite PASS.

## Composite output template

```
Composite verdict: PASS | FAIL | INCONCLUSIVE
Task ID: ...
Diff scope: [files count / paths]

Reviewer summaries:
- architecture: PASS|FAIL|INCONCLUSIVE — [one line]
- product: ...
- security: ...
- runtime: ...
- test: ...

Blocking findings (all reviewers):
- [Reviewer] ID — file:line — problem

Verification evidence:
- [commands and results]

Required next action:
- [implement fixes | re-run tests | owner decision | none]
```

## Independence rule

Collect reviewer outputs only after all five complete. Never let one reviewer see another's draft output during analysis.

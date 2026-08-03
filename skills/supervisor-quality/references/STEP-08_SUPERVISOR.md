# Step 8 - Review and Supervisor Layer

Paste this prompt into Codex inside the `CodexClaw/` project.

## Goal

Add a real review layer without relying on imaginary plugin flows.

## Layer 1 - Built-in Codex review

Use the built-in review command after meaningful code changes:

```bash
codex review --uncommitted
```

Add to `AGENTS.md`:

```markdown
## Review
- After meaningful code changes, run a review before finalizing when possible
- Look for regressions, edge cases, and missing tests
- Fix valid findings before reporting completion
```

## Layer 2 - Optional second model

If you already have Claude Code CLI installed, use it as a separate second opinion.

Do not describe this as a Codex plugin unless you have verified that exact flow live.

Example policy for `AGENTS.md`:

```markdown
## Second Opinion
- If another coding agent is installed locally, use it for high-risk reviews when useful
- Treat external review as advisory
- Prefer concrete bugs and regressions over style comments
```

## Layer 3 - Self-audit command

Add a bot command `/selfaudit`.

Behavior:

1. Check core capabilities:
   - text replies
   - media intake
   - memory files
   - skills presence
   - tool config
2. Report:
   - works
   - broken
   - missing config
3. Save a short health-check entry to `memory/agent-memory.md`

Implement `/selfaudit` in `src/bot.ts`.

## After Implementation

Verify:

1. `codex review --uncommitted` runs
2. `/selfaudit` returns a structured report
3. A health-check entry is saved

Then restart:

```bash
npm run build
pm2 restart codexclaw
```

## Tell The User

```text
Review layer is ready.

You now have:
1. built-in Codex review
2. optional second-opinion workflow
3. /selfaudit health check

Your CodexClaw stack is assembled.
```

# Step 6 - Management Commands

Paste this prompt into Codex inside the `CodexClaw/` project.

## Goal

Implement management commands at the bot layer, not only in `AGENTS.md`.

Reason:

- this bot runs fresh `codex exec` for each message
- commands like `/status` and `/clear` should be handled deterministically in `src/bot.ts`

## Commands To Implement

Add these commands in `src/bot.ts`:

### `/checkpoint`

- Ask Codex to create a concise checkpoint from current files and save it into `memory/agent-memory.md`
- Reply with a short confirmation

### `/newchat`

- Save a checkpoint first
- Reply that the next message already starts as a fresh run
- Do not pretend to clear a live Codex session, because there is none

### `/status`

Implement directly in Node by reading:

- `memory/agent-memory.md`
- `memory/session-summary.md`
- PM2 process is optional, do not depend on it here

Reply with:

- whether memory files exist
- entry count in `memory/agent-memory.md`
- whether `session-summary.md` is empty or not

### `/clear`

- Clear only `memory/session-summary.md`
- Reply: `Session summary cleared. Long-term memory kept.`

### `/compact`

- Summarize the recent working context into `memory/session-summary.md`
- Keep it short
- Reply with the saved summary

### `/dream`

- Ask Codex to consolidate `memory/agent-memory.md`
- Remove duplicates
- Merge near-identical entries
- Keep stable facts and decisions
- Warn in the reply that `/dream` is best used weekly, not daily, because large memory files can consume extra tokens

## Implementation Rules

- Commands are regular Telegram text messages
- If the message exactly matches a command, handle it in `src/bot.ts`
- Do not pass these raw commands into Codex unchanged
- Keep command handling serialized through the same queue

## After Implementation

Verify:

1. `/status`
2. `/checkpoint`
3. `/compact`
4. `/clear`
5. `/dream`

Then restart:

```bash
npm run build
pm2 restart codexclaw
```

## Tell The User

```text
Commands are ready:

/checkpoint
/newchat
/status
/clear
/compact
/dream

Next step: STEP-07_TOOLS.md
```

## Practical Note

- `/dream` is a maintenance command. Recommend it weekly or after heavy work, not every day.

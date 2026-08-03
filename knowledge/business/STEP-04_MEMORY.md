# Step 4 - File-Based Memory System

Paste this prompt into Codex inside the `CodexClaw/` project.

## Architecture

This bot is stateless at process level:

- each Telegram message starts a fresh `codex exec`
- durable memory must live in files

So memory in this setup is:

1. `AGENTS.md` - stable operating rules
2. `memory/agent-memory.md` - long-term facts, decisions, preferences
3. `~/obsidian-vault/` - deep external knowledge base

## Goal

Implement a file-based memory system that survives fresh Codex runs.

## Beginner Workflow - Obsidian from zero

Use this exact workflow for viewers who do not have Obsidian set up yet.

- Trigger: the viewer wants Codex to read and save notes in Obsidian
- Inputs: Obsidian app, one vault folder, optional sync method to server
- Outputs: a real markdown vault that Codex can read and write
- Risk level: low on one machine, medium if the bot runs on a separate VPS

### What a beginner needs

1. Install Obsidian on the main computer
2. Create one vault, for example `obsidian-vault`
3. Create these folders inside it:

```text
Inbox/
Notes/
Projects/
SessionsCodex/
```

4. Put at least one or two markdown notes into the vault so the agent has something to read

### If the bot runs on the same machine

This is the easiest path:

- keep the vault locally at `~/obsidian-vault/`
- point Codex to that folder

### If the bot runs on a VPS

The viewer needs one extra step: a copy of the vault must exist on the server.

Recommended options:

1. Obsidian Sync plus server-side sync helper
2. Syncthing
3. `rsync`

Important:

- Codex does not talk to Obsidian through an API
- Codex works with the vault as a normal folder of `.md` files
- the sync layer only makes sure the same files exist on the server

## Files To Create

```text
memory/
  agent-memory.md
  session-summary.md
```

## 1. Update `AGENTS.md`

Rewrite or expand `AGENTS.md` so it includes:

- owner profile
- communication rules
- file locations
- memory protocol
- Obsidian lookup rules

Use this structure:

```markdown
# CodexClaw

You are Igor's AI assistant, accessible through Telegram.

## Owner
- Name: Igor
- Language: Russian by default
- Style: direct, concise, useful
- Decision filter: saves time or increases income

## Communication
- Lead with the result
- Keep replies concise
- Ask one short question only when required
- Use Markdown formatting that works in Telegram

## Workspace
- Project root: current directory
- Inbox: `workspace/inbox/`
- Output: `workspace/output/`
- Long-term memory: `memory/agent-memory.md`
- Short session summary: `memory/session-summary.md`
- Obsidian vault: `~/obsidian-vault/`

## Memory Protocol
- Before thematic answers, check `memory/agent-memory.md` if relevant
- If `memory/session-summary.md` exists, use it as lightweight carry-over context
- After significant tasks, update `memory/agent-memory.md`
- Use `~/obsidian-vault/` for deep lookup when the topic is known
- Avoid duplicate memory entries
```

Ask the user for any owner details still missing and fill them in.

## 2. Create `memory/agent-memory.md`

Use:

```markdown
# Agent Memory

Long-term facts, decisions, and stable preferences.

## Entries
```

Entry format:

```markdown
### YYYY-MM-DD - Title
- Category: fact | decision | preference | workflow | project
- Content: ...
- Source: user | task | file | observation
```

## 3. Create `memory/session-summary.md`

Use:

```markdown
# Session Summary

Short carry-over context for recent work.
```

This file is optional and can be cleared when no longer useful.

## 4. Obsidian integration

Check whether the vault exists:

```bash
ls ~/obsidian-vault/ 2>/dev/null || echo "No vault found"
```

If it does not exist, create:

```bash
mkdir -p ~/obsidian-vault/{Inbox,Notes,Projects,SessionsCodex}
```

Add clear lookup rules to `AGENTS.md`:

- use vault-first lookup for known topics
- save substantial session notes under `~/obsidian-vault/SessionsCodex/`
- keep session notes concise

### If the viewer already has server-side Obsidian Sync

Use the real folder that already syncs, for example:

```text
/root/obsidian-vault/
```

and store Codex session notes in:

```text
/root/obsidian-vault/SessionsCodex/
```

## 5. Memory behavior

Make sure the bot can now do these tasks reliably:

- answer "What do you know about me?"
- remember stable preferences by writing to `memory/agent-memory.md`
- use `memory/session-summary.md` for short recent context when relevant

## After Implementation

Verify:

1. `AGENTS.md` exists and is filled in
2. `memory/agent-memory.md` exists
3. `memory/session-summary.md` exists
4. Obsidian vault is reachable

Then restart:

```bash
npm run build
pm2 restart codexclaw
```

## Tell The User

```text
Memory is live.

Layers:
1. AGENTS.md
2. memory/agent-memory.md
3. Obsidian vault

Next step: STEP-05_SKILLS.md
```

## What To Say In The Video

Use a short explanation like this:

```text
If you already use Obsidian, great: Codex just works with your vault as a normal folder of markdown files.

If you start from zero, install Obsidian, create one vault, add a few folders and notes, and make sure the same vault exists on the machine where Codex runs.

There is no magic API here. Codex simply reads and writes markdown files, and your sync layer keeps them available across devices.
```

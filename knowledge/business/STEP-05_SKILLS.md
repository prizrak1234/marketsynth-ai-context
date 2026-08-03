# Step 5 - Skills

Paste this prompt into Codex inside the `CodexClaw/` project.

## Goal

Set up skills so the agent handles repeatable tasks more reliably.

## Part 1 - Official curated skills

Inside Codex, inspect available skills:

```text
/skills
```

If skill installation is available, install these curated skills:

1. `imagegen`
2. `doc`
3. `slides`

Verify again:

```text
/skills
```

## Part 2 - Project-local custom skill

Create a project-local skill:

```text
.codex/skills/youtube-parser/
  SKILL.md
  reference/template.md
```

### `.codex/skills/youtube-parser/SKILL.md`

```markdown
---
name: youtube-parser
description: Analyze a YouTube video by URL, extract key points, and save a structured note.
---

# YouTube Parser

## When To Use
Use when the user sends a YouTube URL and asks to analyze, summarize, or extract takeaways.

## Workflow
1. Identify title and channel
2. Get transcript if available
3. Produce:
   - short summary
   - key points
   - takeaways
   - action ideas
4. Save note to `workspace/output/notes/` or Obsidian if requested

## Rules
- Always keep the source URL
- Match the user's language
- Keep the summary focused and non-generic
```

### `.codex/skills/youtube-parser/reference/template.md`

```markdown
---
title: "[VIDEO_TITLE]"
url: "[URL]"
channel: "[CHANNEL]"
date: YYYY-MM-DD
tags: [youtube]
---

# [VIDEO_TITLE]

## Summary
[3-5 sentences]

## Key Points
- Point 1
- Point 2

## Takeaways
- Takeaway 1

## Action Ideas
- Idea 1
```

## Part 3 - Discovery rules

Add to `AGENTS.md`:

```markdown
## Skills
- Check available skills before handling repeatable specialist tasks
- Prefer project-local skills in `.codex/skills/` when they fit
- Use curated skills when installed and relevant
```

## After Implementation

Verify:

1. `/skills` shows installed curated skills if available
2. `.codex/skills/youtube-parser/SKILL.md` exists
3. A test YouTube analysis works

## Tell The User

```text
Skills are ready.

Installed or configured:
- imagegen
- doc
- slides
- youtube-parser

Next step: STEP-06_COMMANDS.md
```

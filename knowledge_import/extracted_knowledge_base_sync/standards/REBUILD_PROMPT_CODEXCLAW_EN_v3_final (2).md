# CodexClaw — Rebuild Prompt For Codex (v3 Final, March 24 2026)

Paste everything below into a fresh Codex session in an empty directory named `CodexClaw/`.

This prompt is for Codex, not Claude.

The goal is not to generate a pile of files.
The goal is to make Codex build a real personal Telegram agent from zero, install the environment, fix machine issues, wire the runtime, and leave behind a service that is already alive and testable.

This should feel clean, simple, and powerful.
A person should be able to paste this once, answer a few credential questions, and watch CodexClaw come online.

---

## YOUR ROLE

You are rebuilding CodexClaw from scratch for Codex.

Create the project, collect the required credentials, install missing prerequisites, build the code, verify it, and start the service.

Start with the banner.
Then inspect the machine.
Then collect secrets.
Then build.
Then verify.
Then launch.

Do not stop after writing files.
Do not stop after printing instructions.
Do not leave a half-finished scaffold.

If something fails, debug it.
If packages are missing, install them.
If the build breaks, repair it.
If the process dies, find out why and fix it.
If a real external blocker remains, state it precisely.

You are not here to propose a project.
You are here to finish one.

---

## WHAT WE'RE BUILDING

```text
 ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗     ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝    ██╔════╝██║     ██╔══██╗██║    ██║
██║     ██║   ██║██║  ██║█████╗   ╚███╔╝     ██║     ██║     ███████║██║ █╗ ██║
██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗     ██║     ██║     ██╔══██║██║███╗██║
╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗    ╚██████╗███████╗██║  ██║╚███╔███╔╝
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

**CodexClaw** is a personal AI assistant powered by **OpenAI Codex CLI** (`@openai/codex`), accessible through Telegram.

It is the OpenAI-side counterpart to ClaudeClaw:
- same persistent-agent spirit
- same practical owner-assistant relationship
- same “message your agent and it does real work” feeling
- different backbone: Codex CLI, Codex sessions, Codex project context, OpenAI-native tooling

**Stack:** Node.js 22 preferred, Node.js 20 acceptable, TypeScript, grammy, Codex CLI via `child_process.spawn`, SQLite via `better-sqlite3`, FTS5, local workspace folders, project context through `AGENTS.md`.

**Key difference from ClaudeClaw:** there is no TypeScript Codex SDK here. CodexClaw must communicate with Codex through `spawn('codex', ['exec', '--json', ...])`, JSONL stdout parsing, session resumption, and reliable final-message capture through `-o <file>`.

**What makes this compelling:**
- you can talk to your own agent in Telegram
- it remembers context locally
- it can keep one Codex session per chat
- it can process files and media, not only text
- it can evolve into a multi-agent operating system around your work
- it lives in your own project folder, database, workspace, and runtime context

**Core capabilities to support:**
- Telegram text messages
- Photos, documents, video, voice, audio intake
- SQLite memory: semantic, episodic, procedural, deep history
- Auto-checkpoint when context grows
- Codex session resumption per chat
- Cron scheduler foundation
- Agent-team scaffolding for YouTube, TikTok, Instagram, content, Obsidian
- Workspace outputs under `workspace/`
- Obsidian-friendly structure and future integrations
- Optional Gemini, Firecrawl, n8n, Whisper, DALL-E paths without breaking the base install

This is not a mockup.
This is not a docs-only skeleton.
Build a real, runnable project that feels impressive because it actually works.

---

## WHY THIS MATTERS

The point is not just “a bot”.
The point is giving one person their own working agent runtime:
- a persistent assistant they can message from anywhere
- a local memory layer they control
- a workspace where outputs, files, and artifacts accumulate
- a system they can extend into research, media, content, automation, and personal operations

The finished result should make people think:
this is much easier than I expected, and much more real than a chatbot wrapper.

---

## THE EXPERIENCE WE WANT

The ideal first run looks like this:

1. The user pastes this prompt into Codex.
2. Codex checks the machine and installs what is missing.
3. Codex asks for the keys and owner identity.
4. Codex generates the project.
5. Codex builds it, fixes install issues, and starts it.
6. The user opens Telegram, sends a first message, and gets a reply from their own Codex-powered assistant.

That is the standard.
Optimize for that outcome.

---

## ARCHITECTURE

```text
Telegram Bot (grammy)
    ↓
Message / media intake
    ↓
Memory Layer (SQLite: semantic + episodic + procedural + deep history)
    ↓
Codex Runner (spawn 'codex exec --json ...')
    ↓ JSONL stdout
Parse events → extract agent_message text + thread_id
    ↓
Response → Telegram

SQLite (store/codexclaw.db):
  - sessions              (session_id per chat)
  - memories              (semantic/episodic/procedural + FTS5)
  - conversation_history  (full messages + FTS5, retention pruning)
  - scheduled_tasks       (cron jobs)
  - agent_runs            (team execution bookkeeping)

Filesystem:
  - AGENTS.md             main Codex runtime context
  - .codex/config.toml    project Codex config
  - workspace/inbox/      inbound files from Telegram
  - workspace/output/     generated outputs and agent artifacts
  - store/                sqlite, pid, logs
```

Runtime flow:

1. Telegram receives the user request.
2. CodexClaw stores conversation context.
3. CodexClaw runs `codex exec` inside the project root.
4. CodexClaw captures the final answer and session id.
5. CodexClaw persists memory and resume state.
6. CodexClaw replies to Telegram and returns files when needed.

Design principle:
- simple enough to understand in one screen
- strong enough to become a serious personal agent platform

---

## HOW CODEX CLI WORKS IN HEADLESS MODE

Use Codex in headless server mode.
The core execution pattern is:

```bash
codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C /path/to/project \
  -m gpt-5.4 \
  -o /tmp/last_message.txt \
  "user prompt here"
```

Flags and behavior:
- `--json` means JSONL events on stdout
- `--dangerously-bypass-approvals-and-sandbox` avoids interactive confirmations for server use
- `--skip-git-repo-check` allows operation outside a git repo
- `-C <DIR>` sets project root and lets Codex read `AGENTS.md`
- `-m <MODEL>` selects the model
- `-o <FILE>` writes the final assistant message to a file and is the most reliable fallback

Session resume support:

```bash
codex exec resume --last "followup prompt"
codex exec resume <session-id> "followup prompt"
```

Auth for bots and headless use:

```bash
CODEX_API_KEY=sk-... codex exec --json "prompt"
```

Default same-machine deployment auth: use existing `codex login` auth from `~/.codex/auth.json` for the same Linux service user when it is present. This is the default path for a personal CodexClaw deployed from a ChatGPT or Codex subscription on one machine.
Preferred portable auth: `CODEX_API_KEY`.
If local `codex login` auth exists, do not ask for `CODEX_API_KEY` first and do not block deployment on that key.
Document the tradeoff clearly:
- `codex login` is the default for same-machine personal deployment via ChatGPT/Codex subscription
- `CODEX_API_KEY` is more portable and survives fresh-machine rebuilds, CI, and service-user changes more reliably
- if the implementation supports both, it should prefer `CODEX_API_KEY` when present and otherwise fall back to local `codex login`

Expected JSONL event shape:

```jsonl
{"type":"thread.started","thread_id":"0199a213-81c0-7800-8aa1-bbab2a035a53"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"bash -lc ls","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_3","type":"agent_message","text":"Response text here."}}
{"type":"turn.completed","usage":{"input_tokens":24763,"cached_input_tokens":24448,"output_tokens":122}}
```

Key parsing rules:
- `thread_id` from `type == "thread.started"` becomes the resumable session id
- final assistant text comes from `type == "item.completed"` where `item.type == "agent_message"`
- `turn.completed` indicates response completion
- `-o <file>` should be used as fallback for the final message text

---

## TARGET ENVIRONMENT

Assume the target machine is:
- Ubuntu or Debian Linux
- shell access available
- `apt` available
- system packages can be installed
- Node.js 22 preferred, Node.js 20 acceptable
- npm available

The project directory is the current working directory.

Canonical layout:

```text
CodexClaw/
├── src/
├── dist/
├── scripts/
├── specs/
├── skills/
├── workspace/
├── store/
├── .codex/
├── AGENTS.md
├── .env
├── .env.example
├── package.json
├── tsconfig.json
└── ecosystem.config.cjs
```

---

## FIRST ACTIONS

Before writing project code:

1. Print a short status line saying you are rebuilding CodexClaw for Codex.
2. Print the ASCII art banner.
3. Inspect the environment.
4. Install missing prerequisites.
5. Then collect the required secrets.

Run checks for:
- `node -v`
- `npm -v`
- `codex --help`
- `/usr/bin/bwrap`

If `/usr/bin/bwrap` is missing, install `bubblewrap`.
If `codex` is missing, install `@openai/codex` globally.
If native Node build prerequisites are missing, install them before continuing.

Typical Linux packages to install when needed:

```bash
apt-get update
apt-get install -y bubblewrap build-essential python3 make g++ pkg-config
```

Install Codex CLI globally if needed:

```bash
npm i -g @openai/codex
```

If `better-sqlite3` later fails to build or load, repair it instead of stopping:

```bash
npm install
npm rebuild better-sqlite3
npm run build
```

---

## CREDENTIALS TO COLLECT

Collect these required values from the user:

```text
1. TELEGRAM_BOT_TOKEN
```

Optional values:

```text
1. CODEX_API_KEY
2. ALLOWED_CHAT_ID
3. OPENAI_API_KEY
4. GOOGLE_API_KEY
5. FIRECRAWL_API_KEY
6. N8N_YOUTUBE_WEBHOOK_URL
7. OWNER_NAME
8. OWNER_HANDLE
```

Rules:
- If optional values are absent, complete the install anyway.
- `ALLOWED_CHAT_ID` must be treated as optional during the very first bootstrap.
- The owner must always be able to discover their chat id safely with `/chatid`.
- `OWNER_NAME` and `OWNER_HANDLE` may default to placeholder values and must not block deployment.
- Default same-machine deployment path: if `~/.codex/auth.json` exists for the runtime user, use it and continue without asking for `CODEX_API_KEY` first.
- `CODEX_API_KEY` is still recommended for portable production deployments, but do not stop installation only because the key is empty when local `codex login` auth exists.

Canonical bootstrap rule:
- if `ALLOWED_CHAT_ID` is already known, use it
- if `ALLOWED_CHAT_ID` is not known, allow `/start` and `/chatid` for first boot, but block normal task execution for unknown chats
- once the owner sends `/chatid`, update `.env` with the returned id
- restart the service
- after restart, enforce the allowlist for all protected commands and normal chat handling

Do not trap the owner in an allowlist dead-end.

---

## FILE STRUCTURE TO CREATE

Create these files and make them work together.

```text
CodexClaw/
├── src/
│   ├── index.ts
│   ├── bot.ts
│   ├── agent.ts
│   ├── memory.ts
│   ├── db.ts
│   ├── config.ts
│   ├── env.ts
│   ├── logger.ts
│   ├── media.ts
│   ├── scheduler.ts
│   ├── team.ts
│   ├── skills.ts
│   └── schedule-cli.ts
├── scripts/
│   ├── setup.ts
│   ├── status.ts
│   └── notify.sh
├── specs/
│   ├── youtube-analysis.md
│   ├── image-generation.md
│   ├── content-factory.md
│   ├── srt-processing.md
│   ├── firecrawl.md
│   ├── gws.md
│   ├── user-profile.md
│   └── agents/
│       ├── README.md
│       ├── youtube-analyzer.md
│       ├── tiktok-analyzer.md
│       ├── instagram-analyzer.md
│       ├── content-writer.md
│       └── obsidian.md
├── skills/
│   ├── README.md
│   ├── youtube-analysis/SKILL.md
│   ├── content-factory/SKILL.md
│   ├── spreadsheet-analysis/SKILL.md
│   ├── pdf-document/SKILL.md
│   ├── telegram-media/SKILL.md
│   └── obsidian-notes/SKILL.md
├── workspace/
│   ├── inbox/
│   ├── output/
│   │   ├── reports/
│   │   ├── presentations/
│   │   ├── exports/
│   │   ├── scripts/
│   │   ├── notes/
│   │   ├── images/
│   │   └── agents/
│   └── tmp/
├── .codex/
│   └── config.toml
├── store/
├── AGENTS.md
├── package.json
├── tsconfig.json
├── .env.example
├── .env
├── ecosystem.config.cjs
└── .gitignore
```

Keep docs concise but real.
Prioritize working code over decorative scaffolding.

---

## IMPLEMENTATION REQUIREMENTS

Use TypeScript with ESM.

At minimum, include these dependencies:

```json
{
  "dependencies": {
    "better-sqlite3": "^11.0.0",
    "cron-parser": "^4.9.0",
    "grammy": "^1.31.0",
    "openai": "^4.0.0",
    "pino": "^9.0.0",
    "pino-pretty": "^11.0.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.13",
    "@types/node": "^22.0.0",
    "tsx": "^4.21.0",
    "typescript": "^5.9.3"
  }
}
```

Use npm unless the user explicitly requests something else.

`package.json` scripts should include at least:

```json
{
  "build": "tsc",
  "start": "node dist/index.js",
  "dev": "tsx src/index.ts",
  "setup": "tsx scripts/setup.ts",
  "status": "tsx scripts/status.ts"
}
```

---

## .ENV EXPECTATIONS

Create `.env.example` and `.env`.

At minimum support these variables:

```env
# Leave empty when using the same Linux user that already has `codex login` auth from a ChatGPT/Codex subscription
# Fill this only when you want portable API-key-based deployment instead of local subscription auth
CODEX_API_KEY=sk-...
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=your_bot_token
ALLOWED_CHAT_ID=
CODEX_MODEL=gpt-5.4
AGENT_TIMEOUT_MS=1200000
GOOGLE_API_KEY=AIza...
FIRECRAWL_API_KEY=fc-...
N8N_YOUTUBE_WEBHOOK_URL=https://example.com/webhook
ENABLE_AUTO_CHECKPOINT=true
ENABLE_DEEP_HISTORY=true
MEMORY_THRESHOLD_WARN=0.70
MEMORY_THRESHOLD_CHECKPOINT=0.80
MEMORY_THRESHOLD_NEW_CHAT=0.85
MEMORY_MAX_CONTEXT_TOKENS=128000
MEMORY_MAX_DEEP_HISTORY_TOKENS=2000
MEMORY_HISTORY_KEEP_DAYS=30
OWNER_NAME=Your Name
OWNER_HANDLE=@yourhandle
```

Rules:
- startup must fail clearly if `TELEGRAM_BOT_TOKEN` is missing
- default same-machine deployment may use local `codex login` auth in `~/.codex/auth.json` for the runtime user
- when `CODEX_API_KEY` is present, the implementation should prefer it over local auth
- if `CODEX_API_KEY` is empty but local `codex login` auth exists in `~/.codex/auth.json`, the bot may still run and this must be documented as a supported default path for subscription-based installs
- `OWNER_NAME` and `OWNER_HANDLE` should default safely and must not be treated as deployment blockers unless the code explicitly requires them
- `OPENAI_API_KEY` may still be used for Whisper or DALL-E pathways
- optional integrations must not break the base bot when unset
- empty `ALLOWED_CHAT_ID` is acceptable only for first bootstrap if `/chatid` and `/start` still work safely

---

## .CODEX CONFIG REQUIREMENTS

Create `.codex/config.toml` with valid Codex configuration for headless operation.
Use real keys, not invented legacy ones.

Use a shape equivalent to:

```toml
model = "gpt-5.4"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[shell_environment_policy]
inherit = "all"
```

Important:
- do not use invalid old keys like `sandbox_permissions`
- use `approval_policy` and `sandbox_mode`
- the goal is unattended server execution

---

## FUNCTIONAL REQUIREMENTS

The rebuilt bot must support these behaviors:

1. Telegram text messages
2. `/start`
3. `/chatid`
4. `/newchat`
5. `/checkpoint`
6. `/convolife`
7. `/recall <query>`
8. `/status`
9. memory persistence in SQLite
10. Codex session resume per chat
11. scheduler table and cron execution foundation
12. media intake path into `workspace/inbox/`
13. file-safe workspace output behavior
14. PID lock protection with stale-PID recovery
15. graceful startup failure messages for missing env or missing Codex CLI
16. safe bootstrap behavior when `ALLOWED_CHAT_ID` is not yet set

If a feature is optional or partial, document it clearly without breaking startup.

---

## CODEX RUNNER REQUIREMENTS

Implement `src/agent.ts` around `spawn('codex', args, ...)`.

Requirements:
- parse JSONL from stdout
- capture `thread_id` from `thread.started`
- capture final assistant text from `item.completed` where `item.type == "agent_message"`
- use `-o <file>` as fallback for final text
- support `resume <session-id>`
- pass `CODEX_API_KEY` to the child process when available
- return a readable error when Codex CLI is missing
- support timeout handling
- support abort handling for killed tasks

Do not use an imaginary Codex TypeScript SDK.

---

## AGENTS.MD REQUIREMENTS

Generate `AGENTS.md` as the runtime behavior file for CodexClaw.

It must define:
- assistant identity as CodexClaw
- concise direct operating style
- no em dash rule
- no sycophancy
- owner identity placeholders based on user input
- task-spec routing
- skills routing
- Obsidian behavior
- workspace output discipline
- agent team behavior
- memory and checkpoint behavior

Make it practical, short, and suitable for repeated Codex usage.

---

## PROCESS MANAGER REQUIREMENTS

Provide `ecosystem.config.cjs` for PM2 with a shape equivalent to:

```js
module.exports = {
  apps: [
    {
      name: 'codexclaw',
      script: 'dist/index.js',
      cwd: '/absolute/path/to/CodexClaw',
      env_file: '.env',
      restart_delay: 5000,
      max_restarts: 10,
      watch: false,
      log_file: 'store/codexclaw.log'
    }
  ]
}
```

If you can generate this from the current working directory instead of a random hardcoded path, do that.

---

## REAL-WORLD TROUBLESHOOTING YOU MUST HANDLE

These are known failure modes. Handle them proactively if they appear.

### 1. Missing system `bwrap`

If Codex reports:

`Codex could not find system bubblewrap at /usr/bin/bwrap`

install and verify:

```bash
apt-get update
apt-get install -y bubblewrap
ls -l /usr/bin/bwrap
```

### 2. Codex CLI missing

If spawning `codex` returns `ENOENT`, install and verify:

```bash
npm i -g @openai/codex
codex --help
```

### 3. Headless auth not configured

If Codex cannot authenticate, check in this order:

1. same-user local subscription auth via `~/.codex/auth.json`
2. if missing, run:

```bash
codex login
```

3. or use portable auth:

```bash
CODEX_API_KEY=sk-...
```

Default personal deployment should succeed through local `codex login` auth when available. Do not force `CODEX_API_KEY` first on a machine that already has valid subscription auth for the runtime user.

### 4. `better-sqlite3` native module problems

If install or runtime fails because `better-sqlite3` did not build correctly:
- install native build prerequisites
- run `npm rebuild better-sqlite3`
- rerun the build
- verify the status script can open the database

### 5. Missing `.env` values

Startup must fail clearly if required values are absent.
Do not hide bad configuration behind silent defaults.

### 6. PID lock issue

CodexClaw uses a PID file in `store/codexclaw.pid`.

If a stale PID file exists:
- verify whether the process is actually running
- if not running, remove the stale PID file
- restart cleanly

Do not leave the service blocked by an orphaned PID file.

### 7. PM2 or process persistence

If PM2 is available, prefer the included ecosystem file for persistent operation.
If PM2 is not available, install it or provide a verified fallback start path.

### 8. Telegram allowlist bootstrap

Do not leave the owner locked out of `/chatid`.
The first-run flow must let the owner discover the correct chat id and then tighten access.

The preferred behavior is:
- unknown users can get `/start` and `/chatid`
- unknown users cannot run normal tasks
- once the owner id is known and written to `.env`, restart and enforce full allowlist behavior

---

## SETUP FLOW YOU MUST EXECUTE

You must actually perform this flow:

1. Inspect environment.
2. Install missing system packages.
3. Install global `@openai/codex` if needed.
4. Check whether `~/.codex/auth.json` already exists for the runtime user.
5. If local `codex login` auth exists, use it as the default deployment path.
6. If local auth does not exist, ask the user whether to authenticate with `codex login` or provide `CODEX_API_KEY`.
7. Generate all project files.
8. Write `.env.example`.
9. Create `.env` using the provided secrets.
10. Run `npm install`.
11. If `better-sqlite3` needs repair, repair it.
12. Run `npm run build`.
13. Run sanity checks:
    - verify `dist/index.js` exists
    - verify `scripts/status.ts` runs
    - verify SQLite DB can initialize
14. Start CodexClaw.
15. Verify the process is alive.
16. If `ALLOWED_CHAT_ID` is empty, explicitly tell the user:
    - open Telegram
    - send `/start`
    - send `/chatid`
    - copy the returned id
17. If `ALLOWED_CHAT_ID` was missing at first, update `.env`, restart the service, and verify the allowlist is now active.
18. Tell the user the exact first normal message to send after bootstrap.

Do not end before the process is running and the bootstrap path is clear.

---

## ACCEPTANCE TESTS

Before declaring success, run and pass these checks.

### File and build checks
- `package.json` exists
- `.env.example` exists
- `AGENTS.md` exists
- `.codex/config.toml` exists
- `npm install` completed
- `npm run build` completed
- `dist/index.js` exists

### Runtime checks
- `scripts/status.ts` executes without crashing
- `store/codexclaw.db` exists after init or start
- `store/codexclaw.pid` is created on start
- the bot process remains alive after startup

### Integration checks
- `codex` command is callable
- `CODEX_API_KEY` is wired into the child process when present
- or local `codex login` auth in `~/.codex/auth.json` is available to the same runtime user
- `TELEGRAM_BOT_TOKEN` is loaded from `.env`
- `/usr/bin/bwrap` exists or you have explicitly verified why vendored fallback is acceptable

### Bootstrap checks
- if `ALLOWED_CHAT_ID` is unset, `/chatid` is still reachable safely
- normal task execution is blocked for unknown chats during bootstrap
- after writing `ALLOWED_CHAT_ID` and restarting, protected behavior is enforced

If any check fails, fix it before finishing.

---

## OUTPUT FORMAT DURING THE BUILD

While working:
- give short progress updates
- name the step you are on
- show failures plainly
- then fix them

At the end provide:
1. what was created
2. what was installed
3. how the service was started
4. what the user should send in Telegram first
5. what optional integrations remain unconfigured

---

## FINAL SUCCESS CONDITION

The task is complete only when all of these are true:

1. The project exists on disk.
2. Dependencies are installed.
3. The project builds successfully.
4. Required env values are present.
5. Codex CLI is callable.
6. CodexClaw has working auth through either local `codex login` subscription auth for the runtime user or `CODEX_API_KEY`.
7. System `bubblewrap` is present at `/usr/bin/bwrap` or the fallback situation is explicitly verified.
8. CodexClaw starts successfully.
9. The user has a clear Telegram bootstrap path.
10. The user has a clear first normal test step.

If you are blocked by missing secrets from the user, stop only after everything else is prepared and clearly state the exact missing values.

---

## START NOW

Rebuild CodexClaw in the current empty directory.

Begin by:
1. printing the ASCII art banner
2. checking the environment
3. installing missing prerequisites
4. collecting required secrets
5. creating the full project
6. building and starting it

Do the work, not just the plan.

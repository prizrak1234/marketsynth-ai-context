# CodexClaw — Rebuild Prompt (v2, March 2026)

Paste everything below into a fresh Claude Code session in an **empty** directory (`codexclaw/`).

---

## YOUR ROLE

You are building CodexClaw from scratch. Create all project files, ask the user for credentials, then build and start the service.

Start with ASCII art. Then collect credentials. Then build.

---

## WHAT WE'RE BUILDING

```
 ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗     ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝    ██╔════╝██║     ██╔══██╗██║    ██║
██║     ██║   ██║██║  ██║█████╗   ╚███╔╝     ██║     ██║     ███████║██║ █╗ ██║
██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗     ██║     ██║     ██╔══██║██║███╗██║
╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗    ╚██████╗███████╗██║  ██║╚███╔███╔╝
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

**CodexClaw** is a personal AI assistant powered by **OpenAI Codex CLI** (`@openai/codex`), accessible via Telegram. The OpenAI equivalent of ClaudeClaw — same architecture, different AI backbone (gpt-5.4 / gpt-5.4-mini instead of Claude).

**Stack:** Node.js 20 + TypeScript + grammy + Codex CLI (child_process spawn) + SQLite (better-sqlite3) + FTS5

**Key difference from ClaudeClaw:** Codex CLI has no TypeScript SDK. Communication happens via `spawn('codex', ['exec', '--json', ...])` with JSONL stdout parsing.

**Features:**
- Text, photos, documents, video, voice messages (Whisper STT)
- 4-layer memory system (SQLite: semantic/episodic/procedural + deep history FTS5)
- Auto-checkpoint when context fills up
- Cron task scheduler
- Parallel agent teams (YouTube, TikTok, Instagram, content factory, Obsidian)
- Obsidian vault integration
- Web scraping (Firecrawl), Google Workspace
- Multi-model routing: Gemini (summarization), DALL-E 3 (images), Whisper (STT)
- n8n webhooks for media analysis

---

## ARCHITECTURE

```
Telegram Bot (grammy)
    ↓
Memory Layer (SQLite: semantic + episodic + deep history)
    ↓
Codex Runner (spawn 'codex exec --json ...')
    ↓ JSONL stdout
Parse events → extract agent_message text + thread_id
    ↓
Response → Telegram

SQLite (store/codexclaw.db):
  - sessions              (session_id per chat)
  - memories              (semantic/episodic/procedural + FTS5)
  - conversation_history  (Layer 2: full messages + FTS5, 30-day retention)
  - scheduled_tasks       (cron jobs)

Context file: AGENTS.md (equivalent of CLAUDE.md in ClaudeClaw)
Config: .codex/config.toml
```

---

## HOW CODEX CLI WORKS IN HEADLESS MODE

```bash
# Primary command for the bot:
codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  -C /path/to/project \
  -m gpt-5.4 \
  -o /tmp/last_message.txt \
  "user prompt here"

# Flags:
# --json            → JSONL events to stdout (one JSON object per line)
# --dangerously-bypass-approvals-and-sandbox → no confirmations (for server)
# -C <DIR>          → working directory (reads AGENTS.md from here)
# -m <MODEL>        → model (gpt-5.4, gpt-5.4-mini)
# -o <FILE>         → write final agent message to file (most reliable way to get output)
# --full-auto       → workspace-write sandbox + on-request approvals preset
# --skip-git-repo-check → allow running outside git repo
# --sandbox <MODE>  → read-only | workspace-write | danger-full-access

# Session resume:
codex exec resume --last "followup prompt"
codex exec resume <session-id> "followup prompt"

# Auth in CI/server (use env var, not interactive login):
CODEX_API_KEY=sk-... codex exec --json "prompt"

# Run as MCP server:
codex mcp-server
```

**JSONL event format (stdout) — VERIFIED from official docs:**
```jsonl
{"type":"thread.started","thread_id":"0199a213-81c0-7800-8aa1-bbab2a035a53"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"bash -lc ls","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_3","type":"agent_message","text":"Response text here."}}
{"type":"turn.completed","usage":{"input_tokens":24763,"cached_input_tokens":24448,"output_tokens":122}}
```

**Key parsing rules:**
- `thread_id` from `type: "thread.started"` → use as session ID for resume
- Final agent response = `item.text` where `item.type === "agent_message"` in `type: "item.completed"` event
- `type: "turn.completed"` = end of response
- **IMPORTANT:** The `-o <file>` flag writes only the final message to a file — most reliable fallback for getting the text

---

## CREDENTIALS TO COLLECT

```
1. OpenAI API Key (sk-... or use CODEX_API_KEY):
2. Telegram Bot Token (from @BotFather):
3. Your Telegram Chat ID (send /chatid after bot starts):
4. Your name/handle (for AGENTS.md personalization):
5. Google API Key (Gemini, optional):
6. Firecrawl API Key (web scraping, optional):
7. n8n YouTube webhook URL (optional):
```

**Note on auth:** For server/CI deployments (headless), use `CODEX_API_KEY` env var — it is supported only in `codex exec` and is the correct approach for bots. Interactive `codex login` (ChatGPT OAuth / device auth) is for local interactive use only.

---

## FILE STRUCTURE

```
codexclaw/
├── src/
│   ├── index.ts         # Entry point, PID lock, init
│   ├── bot.ts           # Telegram bot (grammy), handlers, commands
│   ├── agent.ts         # Codex CLI runner (spawn + JSONL parser)
│   ├── memory.ts        # Memory layers, decay, auto-checkpoint
│   ├── db.ts            # SQLite: sessions, memories, history, tasks
│   ├── config.ts        # Env vars, MEMORY_CONFIG, AGENT_CONFIG
│   ├── env.ts           # .env file reader
│   ├── logger.ts        # Pino logger
│   ├── media.ts         # Telegram media download, Whisper STT
│   ├── scheduler.ts     # Cron task runner
│   └── schedule-cli.ts  # CLI for creating scheduled tasks
├── scripts/
│   ├── setup.ts         # Interactive setup wizard
│   ├── status.ts        # Service status
│   └── notify.sh        # Send Telegram notifications
├── specs/               # Task specifications
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
├── workspace/
│   ├── inbox/
│   ├── output/
│   │   ├── presentations/
│   │   ├── reports/
│   │   ├── exports/
│   │   ├── scripts/
│   │   ├── notes/YouTube/
│   │   ├── images/
│   │   └── agents/
│   └── tmp/
├── .codex/
│   └── config.toml      # Codex CLI project config
├── store/               # SQLite database (gitignored)
├── dist/                # TypeScript build
├── AGENTS.md            # Main context file (like CLAUDE.md)
├── package.json
├── tsconfig.json
├── .env
├── .env.example
└── .gitignore
```

---

## package.json

```json
{
  "name": "codexclaw",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx src/index.ts",
    "setup": "tsx scripts/setup.ts",
    "status": "tsx scripts/status.ts"
  },
  "engines": { "node": ">=20" },
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

**Install globally (prerequisite):**
```bash
npm i -g @openai/codex
```

---

## tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## .env.example

```env
# OpenAI (primary — use CODEX_API_KEY for codex exec, OPENAI_API_KEY for Whisper/DALL-E)
CODEX_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
ALLOWED_CHAT_ID=your_chat_id

# Codex model
CODEX_MODEL=gpt-5.4

# Agent timeout (ms)
AGENT_TIMEOUT_MS=1200000

# Additional models
GOOGLE_API_KEY=AIza...        # Gemini, optional

# Web scraping
FIRECRAWL_API_KEY=fc-...      # optional

# Memory
ENABLE_AUTO_CHECKPOINT=true
ENABLE_DEEP_HISTORY=true
MEMORY_THRESHOLD_WARN=0.70
MEMORY_THRESHOLD_CHECKPOINT=0.80
MEMORY_THRESHOLD_NEW_CHAT=0.85
MEMORY_MAX_CONTEXT_TOKENS=128000
MEMORY_MAX_DEEP_HISTORY_TOKENS=2000
MEMORY_HISTORY_KEEP_DAYS=30
```

---

## .codex/config.toml

```toml
# CodexClaw project configuration
# Verified keys from official Codex docs (March 2026)

model = "gpt-5.4"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[shell_environment_policy]
inherit = "all"
```

**Note:** `sandbox_permissions` from older versions is NOT a valid key. Use `sandbox_mode` and `approval_policy` instead.
- `approval_policy = "never"` — no approval prompts (required for headless bot)
- `sandbox_mode = "danger-full-access"` — full access (use inside isolated server/container)

---

## src/agent.ts — CORE (Codex CLI runner)

```typescript
import { spawn } from 'child_process'
import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { randomUUID } from 'crypto'
import { logger } from './logger.js'
import { PROJECT_ROOT, AGENT_CONFIG } from './config.js'

// JSONL event types from official Codex docs
interface CodexEvent {
  type?: string
  thread_id?: string       // from type: "thread.started"
  item?: {
    id?: string
    type?: string          // "agent_message" | "command_execution" | "reasoning" | etc.
    text?: string          // present when type === "agent_message"
    status?: string
  }
  usage?: {
    input_tokens?: number
    cached_input_tokens?: number
    output_tokens?: number
  }
}

export async function runCodex(
  message: string,
  sessionId?: string,
  onProgress?: () => void,
  abortController?: AbortController
): Promise<{ text: string | null; newSessionId?: string }> {

  const outputFile = join(tmpdir(), `codexclaw-${randomUUID()}.txt`)

  return new Promise((resolve) => {
    const args: string[] = ['exec']

    // Session resumption
    if (sessionId) {
      args.push('resume', sessionId)
    }

    args.push(
      '--json',
      '--dangerously-bypass-approvals-and-sandbox',
      '--skip-git-repo-check',
      '-C', PROJECT_ROOT,
      '-m', AGENT_CONFIG.MODEL,
      '-o', outputFile    // write final message to file (most reliable)
    )

    // Prompt goes last
    args.push(message)

    let newSessionId: string | undefined
    let lastText: string | null = null
    let jsonlBuffer = ''
    let aborted = false

    // Timeout
    const timeoutId = setTimeout(() => {
      if (!aborted) {
        aborted = true
        proc.kill('SIGTERM')
        resolve({ text: '__TIMEOUT__', newSessionId })
      }
    }, AGENT_CONFIG.TIMEOUT_MS)

    const proc = spawn('codex', args, {
      env: {
        ...process.env,
        // CODEX_API_KEY is the correct env var for codex exec (not OPENAI_API_KEY)
        CODEX_API_KEY: process.env.CODEX_API_KEY ?? process.env.OPENAI_API_KEY ?? '',
        OPENAI_API_KEY: process.env.OPENAI_API_KEY ?? '', // for Whisper/DALL-E calls
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    // Progress / typing indicator
    const typingInterval = onProgress ? setInterval(onProgress, 4000) : null

    // Parse JSONL events — verified format from official Codex docs
    proc.stdout.on('data', (chunk: Buffer) => {
      jsonlBuffer += chunk.toString()
      const lines = jsonlBuffer.split('\n')
      jsonlBuffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const event: CodexEvent = JSON.parse(line)

          // Capture thread_id as session ID for resume
          if (event.type === 'thread.started' && event.thread_id) {
            newSessionId = event.thread_id
          }

          // Capture agent message text
          // Official format: type="item.completed", item.type="agent_message", item.text="..."
          if (
            event.type === 'item.completed' &&
            event.item?.type === 'agent_message' &&
            event.item?.text
          ) {
            lastText = event.item.text
          }
        } catch {
          // Non-JSON line, skip
        }
      }
    })

    proc.stderr.on('data', (data: Buffer) => {
      logger.debug({ stderr: data.toString().slice(0, 200) }, 'codex stderr')
    })

    proc.on('close', (code) => {
      clearTimeout(timeoutId)
      if (typingInterval) clearInterval(typingInterval)

      if (aborted) return

      // Prefer -o output file (most reliable for final message)
      if (existsSync(outputFile)) {
        try {
          const fileContent = readFileSync(outputFile, 'utf-8').trim()
          if (fileContent) lastText = fileContent
        } catch (e) {
          logger.warn({ e }, 'Could not read output file')
        }
        try { unlinkSync(outputFile) } catch {}
      }

      if (code !== 0 && !lastText) {
        logger.warn({ code }, 'codex process exited with non-zero code and no output')
        resolve({
          text: `Error: Codex process exited with code ${code}. Check CODEX_API_KEY is set and codex is installed (npm i -g @openai/codex).`
        })
        return
      }

      resolve({ text: lastText, newSessionId })
    })

    proc.on('error', (err: NodeJS.ErrnoException) => {
      clearTimeout(timeoutId)
      if (typingInterval) clearInterval(typingInterval)
      logger.error({ err }, 'Failed to spawn codex')
      if (err.code === 'ENOENT') {
        resolve({ text: 'Codex CLI not found. Install it: npm i -g @openai/codex' })
      } else {
        resolve({ text: `Spawn error: ${err.message}` })
      }
    })

    // /kill support
    abortController?.signal.addEventListener('abort', () => {
      if (!aborted) {
        aborted = true
        clearTimeout(timeoutId)
        proc.kill('SIGTERM')
        resolve({ text: '__KILLED__', newSessionId })
      }
    })
  })
}
```

---

## MULTI-MODEL ROUTING

| Task type | Model/Tool |
|-----------|------------|
| Complex reasoning, code, analysis | gpt-5.4 (default) |
| Fast/cheap tasks, subagents | gpt-5.4-mini |
| Image generation | DALL-E 3 via OPENAI_API_KEY |
| Summarization, classification | gemini-2.5-flash via GOOGLE_API_KEY |
| Voice transcription | Whisper via OPENAI_API_KEY |

Image generation (DALL-E 3):
```bash
curl -s https://api.openai.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"dall-e-3","prompt":"PROMPT","n":1,"size":"1024x1024"}' \
  | jq -r '.data[0].url'
```

Gemini API:
```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"PROMPT"}]}]}'
```

---

## AGENTS.md (adapt for your user)

```markdown
# CodexClaw

You are [NAME]'s personal AI assistant, accessible via Telegram.
You run as a persistent service on their machine using OpenAI Codex CLI.

## Personality

Your name is CodexClaw. You are chill, grounded, and straight up.

Rules you never break:
- No em dashes. Ever.
- No AI clichés. Never say "Certainly!", "Great question!", "I'd be happy to".
- No sycophancy.
- No excessive apologies. Fix it and move on.
- Don't narrate what you're about to do. Just do it.
- If you don't know something, say so plainly.

## Who Is [USERNAME]

[Brief description: profession, tech stack, projects, communication language]

## Task Specs

Read the spec file before executing any matching task:

| File | Task type |
|------|-----------|
| `specs/youtube-analysis.md` | YouTube video analysis |
| `specs/image-generation.md` | Image generation (DALL-E 3) |
| `specs/content-factory.md` | Social media content |
| `specs/srt-processing.md` | Subtitle processing |
| `specs/firecrawl.md` | Web scraping |
| `specs/gws.md` | Google Workspace |
| `specs/agents/README.md` | Agent Teams orchestration |

## Your Job

Execute. Don't narrate. Output first.

## Your Environment

- Tools: Bash, file system, web search, all MCP servers
- Project root: directory where AGENTS.md is located
- Obsidian vault: ~/obsidian-vault
- Default model: gpt-5.4 (use gpt-5.4-mini for fast/cheap tasks)

## Multi-Model Routing

| Task type | Model/Tool |
|-----------|------------|
| Complex reasoning, code, analysis | gpt-5.4 (default) |
| Fast/cheap tasks, subagents | gpt-5.4-mini |
| Image generation | DALL-E 3 via OPENAI_API_KEY |
| Summarization, classification | gemini-2.5-flash via GOOGLE_API_KEY |
| Voice transcription | Whisper via OPENAI_API_KEY |

## Agent Teams

Available: youtube-analyzer, tiktok-analyzer, instagram-analyzer, content-writer, obsidian
Specs: specs/agents/{agent-name}.md

Triggers:
- Multiple YouTube URLs → parallel youtube-analyzer per URL
- TikTok URL → tiktok-analyzer
- Instagram Reel → instagram-analyzer
- "content for all platforms" → content-writer x3
- Before 3+ agents → show plan, ask for confirmation

## Workspace Structure

| Folder | Purpose |
|--------|---------|
| `workspace/inbox/` | Files from user via Telegram |
| `workspace/output/reports/` | Reports, analyses |
| `workspace/output/notes/` | Notes, summaries |
| `workspace/output/images/` | Generated images |
| `workspace/output/agents/{task_id}/` | Agent artifacts |
| `workspace/tmp/` | Temporary files |

## Message Format

- Tight, readable responses
- Plain text over heavy markdown
- Voice messages: `[Voice transcribed]: ...` — treat as normal text

## Session Notes (auto)

After tasks with 5+ tool calls, save brief note to Obsidian:
- Path: `~/obsidian-vault/Sessions/YYYY-MM-DD-{task-slug}.md`

## Special Commands

### `convolife`
Estimate context usage based on conversation history row count.
Report: "Context estimate: ~Xk tokens used (gpt-5.4 window)"

### `checkpoint`
Save to SQLite + Obsidian:
1. Write 3-5 bullet summary
2. DELETE existing row for today's topic_key, INSERT at salience=5.0
3. Save to ~/obsidian-vault/Sessions/YYYY-MM-DD-checkpoint.md
4. Reply: "Checkpoint saved. Safe to /newchat."
```

---

## BOT COMMANDS (identical to ClaudeClaw)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/chatid` | Show Chat ID |
| `/newchat` | Clear session |
| `/checkpoint` | Save session summary |
| `/convolife` | Context usage estimate |
| `/recall <query>` | Search conversation history |
| `/status` | Active task status |
| `/kill` | Abort current task (SIGTERM to codex process) |
| `/memory` | Show stored memories |
| `/schedule` | Manage scheduled tasks |

---

## KEY IMPLEMENTATION DIFFERENCES vs ClaudeClaw

### agent.ts
| | ClaudeClaw | CodexClaw |
|-|------------|-----------|
| Engine | `@anthropic-ai/claude-agent-sdk` query() | `spawn('codex', ['exec', '--json', ...])` |
| Session ID source | `system/init` SDK event | `thread_id` from `type: "thread.started"` JSONL |
| Resume | `options.resume: sessionId` | `codex exec resume <thread_id> "prompt"` |
| Response text | SDK result event | `item.text` where `item.type === "agent_message"` in `item.completed` |
| Context file | `CLAUDE.md` | `AGENTS.md` |
| Auth env var | `ANTHROPIC_API_KEY` | `CODEX_API_KEY` (for exec) + `OPENAI_API_KEY` (for Whisper/DALL-E) |
| Models | Claude Sonnet/Opus | gpt-5.4 / gpt-5.4-mini |
| Image gen | Nano Banana 2 (KIE_AI_KEY) | DALL-E 3 (OPENAI_API_KEY) |
| Context window | 200k tokens | 128k tokens (gpt-5.4) |
| convolife | Reads JSONL precisely | Estimates from history count |

### Memory system
Identical to ClaudeClaw:
- Layer 1: semantic/episodic/procedural memories with FTS5
- Layer 2: conversation_history with FTS5 + /recall
- Layer 3: auto-checkpoint at 80/85% context

---

## SQLITE SCHEMA (identical to ClaudeClaw)

```sql
CREATE TABLE sessions (
  chat_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,     -- stores thread_id from Codex
  updated_at INTEGER NOT NULL
);

CREATE TABLE memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  topic_key TEXT,
  content TEXT NOT NULL,
  sector TEXT CHECK(sector IN ('semantic','episodic','procedural')),
  salience REAL DEFAULT 1.0,
  created_at INTEGER NOT NULL,
  accessed_at INTEGER NOT NULL,
  parent_topic TEXT,
  tags TEXT
);
CREATE VIRTUAL TABLE memories_fts USING fts5(
  content, content='memories', content_rowid='id'
);

CREATE TABLE conversation_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  session_id TEXT,
  role TEXT CHECK(role IN ('user','assistant')),
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE VIRTUAL TABLE conversation_history_fts USING fts5(
  content, content='conversation_history', content_rowid='id'
);

CREATE TABLE scheduled_tasks (
  id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  schedule TEXT NOT NULL,
  next_run INTEGER NOT NULL,
  last_run INTEGER,
  last_result TEXT,
  status TEXT CHECK(status IN ('active','paused')),
  created_at INTEGER NOT NULL
);
```

---

## INSTALLATION & STARTUP

```bash
# 1. Prerequisite: install Codex CLI globally
npm i -g @openai/codex

# 2. Verify
codex --version

# 3. Test headless mode (verify JSONL output format)
CODEX_API_KEY=sk-... codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  --json \
  "Say hello and nothing else"
# Expected output: lines starting with {"type":"thread.started",...} etc.
# Find the line with "item.type":"agent_message" — that contains the response text

# 4. Build project
npm install
npm run build

# 5. Configure
cp .env.example .env
# Fill in CODEX_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID

# 6. Start
npm start

# Or via PM2:
pm2 start dist/index.js --name codexclaw
pm2 save && pm2 startup
```

---

## DEBUGGING CODEX CLI

```bash
# 1. Test JSONL output — inspect actual event schema
CODEX_API_KEY=sk-... codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  "Say hello" 2>&1 | head -20

# 2. Write response to file (most reliable for getting output text)
CODEX_API_KEY=sk-... codex exec \
  -o /tmp/test.txt \
  --dangerously-bypass-approvals-and-sandbox \
  "What is 2+2?"
cat /tmp/test.txt

# 3. Test session resume
# Step 1: run first prompt, note thread_id from "thread.started" event
THREAD_ID=$(CODEX_API_KEY=sk-... codex exec --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "Remember the number 42" 2>&1 | python3 -c "import sys,json; [print(j['thread_id']) for line in sys.stdin for j in [json.loads(line)] if j.get('type')=='thread.started']")
echo "Thread ID: $THREAD_ID"

# Step 2: resume
CODEX_API_KEY=sk-... codex exec resume $THREAD_ID \
  --dangerously-bypass-approvals-and-sandbox \
  "What number did I ask you to remember?"

# 4. Run as MCP server (alternative integration approach)
codex mcp-server --port 3000

# 5. Check version
codex --version
```

---

## PM2 DEPLOYMENT

```javascript
// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'codexclaw',
    script: 'dist/index.js',
    cwd: '/root/codexclaw',
    env_file: '.env',
    restart_delay: 5000,
    max_restarts: 10,
    watch: false,
    log_file: 'store/codexclaw.log',
  }]
}
```

---

## .gitignore

```
node_modules/
dist/
.env
store/
workspace/inbox/*
workspace/tmp/*
workspace/output/*
```

---

## POST-BUILD VERIFICATION

```bash
# 1. Codex CLI works (check JSONL format)
CODEX_API_KEY=sk-... codex exec \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "ping" 2>&1

# 2. Bot starts
npm start

# 3. /chatid → get Chat ID
# 4. Send text → Codex responds
# 5. /memory → stored memories list
# 6. /kill → abort task
# 7. /schedule list → task list
```

---

## WHAT CHANGED vs v1

1. **JSONL parser rewritten** — now uses verified event format: `type: "item.completed"`, `item.type: "agent_message"`, `item.text` for response text; `thread_id` from `type: "thread.started"` for session tracking
2. **Auth clarified** — `CODEX_API_KEY` env var for `codex exec` (server/CI mode); `OPENAI_API_KEY` kept for Whisper/DALL-E; interactive `codex login` is for local interactive use only
3. **config.toml fixed** — replaced invalid `sandbox_permissions` key with correct `approval_policy = "never"` and `sandbox_mode = "danger-full-access"` per official docs
4. **Models updated** — replaced `o3`/`o4-mini` with current `gpt-5.4` / `gpt-5.4-mini` (o3/o4-mini are succeeded models as of March 2026)
5. **tsconfig.json added** — was missing in v1, now matches ClaudeClaw
6. **.env.example added** — was missing in v1 (cp .env.example .env now works correctly)
7. **scripts/status.ts added** to file structure and package.json scripts
8. **Debugging section updated** — added script to extract thread_id and test resume correctly

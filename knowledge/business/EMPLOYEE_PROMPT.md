# Employee Builder — Prompt v1

Paste everything below into a fresh Claude Code session inside an empty directory (e.g. `ClaudeHR/`).

---

## YOUR ROLE

You are building a minimal AI employee that runs on this server and is accessible via Telegram.

After the build, this employee will act as an **HR Manager** — it can create other employees on the same server by copying itself, writing a new `CLAUDE.md`, and starting a new Telegram bot.

Do not add anything beyond what is specified. No voice, no media, no scheduler — keep it minimal and reliable.

---

## WHAT WE'RE BUILDING

A lightweight Telegram bot powered by Claude Code:

```
Telegram → grammy (Node.js) → Claude Agent SDK → CLAUDE.md (role instructions)
```

Stack: **Node.js 22 + TypeScript + grammy + @anthropic-ai/claude-agent-sdk**

---

## REQUIRED BEFORE STARTING

Ask the user for these two values:

1. **TELEGRAM_BOT_TOKEN** — from @BotFather in Telegram
2. **ALLOWED_CHAT_ID** — their Telegram user ID (get it from @userinfobot)

Do not proceed until both are provided.

---

## BUILD STEPS

1. Collect credentials from user
2. Create all project files from specs below
3. Write `.env` with the collected credentials
4. Run `npm install`
5. Run `npm run build`
6. Start with pm2: `pm2 start npm --name "$(basename $PWD)" -- start && pm2 save`
7. Run `pm2 startup` and show the user the output command to run (for auto-restart on reboot)
8. Verify bot is running: `pm2 list`
9. Report success: tell user to open Telegram and write to their bot

---

## PROJECT FILES

### `package.json`

```json
{
  "name": "employee",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "engines": { "node": ">=22" },
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.2.59",
    "grammy": "^1.31.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "typescript": "^5"
  }
}
```

---

### `tsconfig.json`

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

### `src/env.ts`

```typescript
import { readFileSync } from 'fs'
import path from 'path'

// Use process.cwd() instead of __dirname because dist/ may be a symlink
// to the master copy. pm2 starts each employee with --cwd /root/[name],
// so process.cwd() always points to the correct employee folder.
export const PROJECT_ROOT = process.cwd()

export function readEnv(): Record<string, string> {
  const envPath = path.join(PROJECT_ROOT, '.env')
  const content = readFileSync(envPath, 'utf-8')
  const env: Record<string, string> = {}
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const idx = trimmed.indexOf('=')
    if (idx === -1) continue
    env[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim()
  }
  return env
}
```

---

### `src/agent.ts`

```typescript
import { query } from '@anthropic-ai/claude-agent-sdk'
import type { SDKMessage } from '@anthropic-ai/claude-agent-sdk'
import { PROJECT_ROOT } from './env.js'

const sessions = new Map<string, string>()

export async function runAgent(
  chatId: string,
  message: string
): Promise<string> {
  let result = ''
  const sessionId = sessions.get(chatId)

  // Strip CLAUDECODE env var to prevent nested session conflicts
  const { CLAUDECODE: _stripped, ...cleanEnv } = process.env as Record<string, string>

  const events = query({
    prompt: message,
    options: {
      cwd: PROJECT_ROOT,
      resume: sessionId,
      systemPrompt: { type: 'preset', preset: 'claude_code' },
      settingSources: ['project', 'user'],
      permissionMode: 'dontAsk',
      env: cleanEnv,
      allowedTools: ['Bash(*)', 'Read(*)', 'Write(*)', 'Edit(*)', 'Glob(*)', 'Grep(*)'],
    },
  })

  for await (const event of events as AsyncGenerator<SDKMessage>) {
    if (event.type === 'system' && event.subtype === 'init') {
      sessions.set(chatId, event.session_id)
    } else if (event.type === 'result') {
      result = event.subtype === 'success'
        ? (event.result ?? '')
        : `Error: ${(event as { errors?: string[] }).errors?.join('; ') ?? 'Agent error'}`
    }
  }

  return result || 'Done.'
}
```

---

### `src/bot.ts`

```typescript
import { Bot } from 'grammy'
import { readEnv } from './env.js'
import { runAgent } from './agent.js'

export function startBot(): void {
  const env = readEnv()
  const token = env['TELEGRAM_BOT_TOKEN']
  const allowedChatId = env['ALLOWED_CHAT_ID']

  if (!token) throw new Error('TELEGRAM_BOT_TOKEN missing in .env')

  const bot = new Bot(token)

  bot.on('message:text', async (ctx) => {
    const chatId = String(ctx.chat.id)
    if (allowedChatId && chatId !== allowedChatId) return

    const typingInterval = setInterval(
      () => ctx.replyWithChatAction('typing').catch(() => {}),
      4000
    )
    try {
      const reply = await runAgent(chatId, ctx.message.text)
      await ctx.reply(reply)
    } catch (e) {
      await ctx.reply(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      clearInterval(typingInterval)
    }
  })

  bot.start()
  console.log('Employee bot started')
}
```

---

### `src/index.ts`

```typescript
import { startBot } from './bot.js'
startBot()
```

---

### `CLAUDE.md`

Write this file as the role instructions for the HR Manager:

```markdown
# HR Manager — AI Employee Creator

You are an HR Manager running on this server.
Your job: create new AI employees on this server when the user asks.

## How employees work

Each employee is a copy of this project folder with two files changed:
- `CLAUDE.md` — defines who the employee is and what they do
- `.env` — contains the Telegram bot token and chat_id

The code (src/, dist/, node_modules/) never changes between employees.

## Your folder

To find your project path, run: `pwd`
Use this path as PROJECT_FOLDER in all commands below.
This folder is the master template — all new employees are cloned from it.

## How to create a new employee

When the user asks to create an employee, follow these steps:

1. Ask for (if not provided): role description, folder name, Telegram bot token, chat_id
2. Check the name is free: `ls /root/ | grep [name]`
3. Copy this project as the base:
   ```
   rsync -a --exclude=node_modules --exclude=dist PROJECT_FOLDER/ /root/[name]/
   ln -s PROJECT_FOLDER/node_modules /root/[name]/node_modules
   ln -s PROJECT_FOLDER/dist /root/[name]/dist
   ```
4. Clean previous data:
   ```
   rm -f /root/[name]/store/*.db 2>/dev/null || true
   ```
5. Write a new `CLAUDE.md` for the role into `/root/[name]/CLAUDE.md`
   — describe who they are, what they know, how they work
   — use the role templates in `/root/[name]/workspace/templates/` as a base
6. Write `/root/[name]/.env`:
   ```
   TELEGRAM_BOT_TOKEN=[token]
   ALLOWED_CHAT_ID=[chat_id]
   ```
7. Start:
   ```
   pm2 start npm --name "[name]" --cwd /root/[name] -- start && pm2 save
   ```
8. Verify: `pm2 list`
9. Reply to user: "Employee ready. Bot is online. Role: [role]. Waiting for documents or commands."

## Role templates

Store reusable role templates as markdown files in `/root/[your_folder]/workspace/templates/`.
Create these templates on first use and expand over time.

## Rules

- Never modify your own CLAUDE.md or .env
- Never delete or overwrite PROJECT_FOLDER (it's the master copy)
- If pm2 fails, show logs: `pm2 logs [name] --lines 20`
- One folder name = one employee. Check before creating.
```

---

### `.env`

```
TELEGRAM_BOT_TOKEN=[filled in during build]
ALLOWED_CHAT_ID=[filled in during build]
```

---

### `workspace/templates/` folder

Create this folder and add three starter templates:

**`workspace/templates/librarian.md`:**
```
You are a knowledge librarian.
All documents are in /workspace/docs/
Before answering, always search: grep -ri "query" /workspace/docs/
Only answer from documents. Always name the source file.
If not found, say so honestly.
Accept new files from the user and save them to /workspace/docs/
```

**`workspace/templates/support.md`:**
```
You are a customer support specialist.
FAQ is in /workspace/docs/faq.md
When a user reports a problem:
1. Ask one clarifying question maximum
2. Search FAQ for a solution
3. If not found, create a ticket: /workspace/tickets/YYYY-MM-DD-topic.md
4. Confirm ticket number to user
Tone: polite, specific, no filler words.
```

**`workspace/templates/sales.md`:**
```
You are a sales manager.
Product catalog: /workspace/docs/catalog.md
Price list: /workspace/docs/price.md
When asked: suggest a suitable product and generate a proposal.
Save proposals to /workspace/proposals/YYYY-MM-DD-client.md
Never invent prices or specs. Only use catalog data.
```

---

## AFTER BUILD

Tell the user:

```
HR Manager is ready.

Open Telegram → find your bot → send any message.

To create a new employee, write:
"Create a support specialist. Token: [token from BotFather]. Chat ID: [your chat_id]."

The HR Manager will deploy the new bot and confirm when it's online.

Before creating any employee — get a new bot token from @BotFather in Telegram.
```

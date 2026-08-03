# Step 2 - Telegram Bridge for Codex

Paste this into a fresh Codex session inside an empty project directory, for example `CodexClaw/`.

## Goal

Build a minimal and reliable Telegram bot that:

`Telegram -> grammY -> codex exec -> AGENTS.md`

Important architecture note:

- Every Telegram message starts a fresh `codex exec` run
- Persistence comes from files like `AGENTS.md`, `memory/*.md`, and Obsidian notes
- We are not building a long-lived in-memory chat session in this step

## Ask The User First

Collect these values before generating files:

1. `TELEGRAM_BOT_TOKEN`
2. `ALLOWED_CHAT_ID`

Do not proceed until both are provided.

## Build Steps

1. Create the project structure
2. Create all files below
3. Write `.env`
4. Run `npm install`
5. Run `npm run build`
6. Start with PM2
7. Run `pm2 startup` and show the command the user must execute
8. Verify with `pm2 list`

## Project Structure

```text
CodexClaw/
  package.json
  tsconfig.json
  .gitignore
  .env
  AGENTS.md
  workspace/
    inbox/
    output/
  src/
    index.ts
    bot.ts
    codex.ts
    env.ts
```

## Files To Create

### `package.json`

```json
{
  "name": "codexclaw",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "engines": {
    "node": ">=22"
  },
  "dependencies": {
    "dotenv": "^16.6.1",
    "grammy": "^1.42.0"
  },
  "devDependencies": {
    "@types/node": "^22.18.0",
    "typescript": "^5.9.2"
  }
}
```

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
    "skipLibCheck": true,
    "esModuleInterop": true
  },
  "include": ["src/**/*.ts"]
}
```

### `.gitignore`

```gitignore
node_modules
dist
.env
workspace/inbox/*
workspace/output/*
!workspace/inbox/.gitkeep
!workspace/output/.gitkeep
```

### `.env`

```env
TELEGRAM_BOT_TOKEN=[fill during setup]
ALLOWED_CHAT_ID=[fill during setup]
```

### `AGENTS.md`

```markdown
# CodexClaw

You are Igor's AI assistant, accessible through Telegram.

## Communication
- Match the user's language
- Lead with the result
- Keep replies concise
- Ask one short question only when required

## Working Style
- Execute tasks, do not dump plans first
- Save generated artifacts under `workspace/output/`
- Save incoming files under `workspace/inbox/`
- If a task is substantial, verify the result before finalizing
- Timeout: 5 minutes per task

## Memory
- Use files in `memory/` and notes in `~/obsidian-vault/` as persistent context when available
```

### `src/env.ts`

```ts
import dotenv from 'dotenv'

dotenv.config()

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} is missing`)
  return value
}

export const env = {
  TELEGRAM_BOT_TOKEN: required('TELEGRAM_BOT_TOKEN'),
  ALLOWED_CHAT_ID: required('ALLOWED_CHAT_ID'),
  PROJECT_ROOT: process.cwd()
}
```

### `src/codex.ts`

```ts
import { spawn } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { env } from './env.js'

export async function runCodex(message: string): Promise<string> {
  const tempDir = mkdtempSync(path.join(tmpdir(), 'codexclaw-'))
  const outputFile = path.join(tempDir, 'last-message.txt')
  const timeoutMs = 5 * 60 * 1000

  return new Promise((resolve, reject) => {
    let finished = false
    const child = spawn(
      'codex',
      [
        'exec',
        '--skip-git-repo-check',
        '--full-auto',
        '-C',
        env.PROJECT_ROOT,
        '-o',
        outputFile,
        message
      ],
      {
        cwd: env.PROJECT_ROOT,
        env: process.env,
        stdio: ['ignore', 'pipe', 'pipe']
      }
    )

    let stderr = ''
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString()
    })

    const timer = setTimeout(() => {
      if (finished) return
      finished = true
      child.kill('SIGTERM')
      rmSync(tempDir, { recursive: true, force: true })
      reject(new Error('Codex timeout: task exceeded 5 minutes'))
    }, timeoutMs)

    child.on('error', (error) => {
      if (finished) return
      finished = true
      clearTimeout(timer)
      rmSync(tempDir, { recursive: true, force: true })
      reject(error)
    })

    child.on('close', (code) => {
      if (finished) return
      finished = true
      clearTimeout(timer)
      try {
        const reply = readFileSync(outputFile, 'utf8').trim()
        rmSync(tempDir, { recursive: true, force: true })
        if (reply) {
          resolve(reply)
          return
        }
      } catch {
        // Fall through to stderr handling below.
      }

      rmSync(tempDir, { recursive: true, force: true })

      if (code === 0) {
        resolve('Done.')
        return
      }

      const message = stderr.trim() || `Codex exited with code ${code ?? 'unknown'}`
      reject(new Error(message))
    })
  })
}
```

### `src/bot.ts`

```ts
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { Bot } from 'grammy'
import { runCodex } from './codex.js'
import { env } from './env.js'

const bot = new Bot(env.TELEGRAM_BOT_TOKEN)

const inboxDir = path.join(env.PROJECT_ROOT, 'workspace', 'inbox')
const outputDir = path.join(env.PROJECT_ROOT, 'workspace', 'output')
mkdirSync(inboxDir, { recursive: true })
mkdirSync(outputDir, { recursive: true })
writeFileSync(path.join(inboxDir, '.gitkeep'), '', { flag: 'a' })
writeFileSync(path.join(outputDir, '.gitkeep'), '', { flag: 'a' })

let queue: Promise<void> = Promise.resolve()

function splitPlainText(text: string, size = 4000): string[] {
  const chunks: string[] = []
  for (let i = 0; i < text.length; i += size) {
    chunks.push(text.slice(i, i + size))
  }
  return chunks.length ? chunks : ['Done.']
}

bot.on('message:text', async (ctx) => {
  if (String(ctx.chat.id) !== env.ALLOWED_CHAT_ID) return

  queue = queue.then(async () => {
    const typing = setInterval(() => {
      ctx.replyWithChatAction('typing').catch(() => {})
    }, 4000)

    try {
      const reply = await runCodex(ctx.message.text)
      for (const chunk of splitPlainText(reply)) {
        await ctx.reply(chunk)
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : String(error)
      await ctx.reply(`Error:\n${text.slice(0, 3500)}`)
    } finally {
      clearInterval(typing)
    }
  })

  await queue
})

export async function startBot(): Promise<void> {
  await bot.start()
  console.log('CodexClaw bot started')
}
```

### `src/index.ts`

```ts
import { startBot } from './bot.js'

startBot().catch((error) => {
  console.error(error)
  process.exit(1)
})
```

## Commands To Run After Files Are Created

```bash
npm install
npm run build
pm2 start npm --name codexclaw -- start
pm2 save
pm2 startup
pm2 list
```

## Verification

1. Send any text message to the bot
2. The bot should answer
3. `pm2 list` should show `codexclaw` as `online`

## Practical Note

- The template now includes a hard timeout of 5 minutes per Codex task so one stuck run does not block the queue forever.

## Tell The User

```text
CodexClaw is running.

Test it in Telegram with a plain text message.

Next step: STEP-03_MEDIA_AND_FORMATTING.md
```

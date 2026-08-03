# ClaudeClaw — Rebuild Prompt (v2, March 2026)

Paste everything below into a fresh Claude Code session in an **empty** directory (`claudeclaw/`).

---

## YOUR ROLE

You are building ClaudeClaw from scratch. Create all project files from the specs below, ask the user for credentials, then build and start the service.

Start with the ASCII art and a short description. Then collect credentials. Then build.

---

## WHAT WE'RE BUILDING

```
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║     ██║     ███████║██║   ██║██║  ██║█████╗
██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝╚══════╝
 ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝██║     ██╔══██╗██║    ██║
██║     ██║     ███████║██║ █╗ ██║
██║     ██║     ██╔══██║██║███╗██║
╚██████╗███████╗██║  ██║╚███╔███╔╝
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

**ClaudeClaw** is a personal AI assistant that runs Claude Code CLI on your server, accessible from anywhere via Telegram.

Stack: Node.js 20 + TypeScript + grammy + @anthropic-ai/claude-agent-sdk + SQLite

Features:
- Text, photos, documents, video, voice messages (Whisper STT)
- 4-layer memory system (SQLite + FTS5)
- Cron task scheduler
- Agent teams (YouTube, TikTok, Instagram analyzers, content factory)
- Auto-checkpoint when context fills up

### Memory Architecture

```
Layer 1a — Semantic memories   (long-term facts, slow decay 0.97/day)
Layer 1b — Episodic memories   (recent activity, fast decay 0.85/day)
Layer 1c — Procedural memories (how-to knowledge, manual salience)
Layer 2  — Full conversation history (FTS5-indexed, 30-day retention)
```

- Layers 1a/1b/1c: `memories` table, FTS5-indexed, salience-weighted, auto-decay
- Layer 2: `conversation_history` table, full message pairs, semantic search via `/recall`
- Auto-checkpoint: saves compressed summary to Layer 1a at salience 5.0 when context > 80%
- `/recall <query>` — injects relevant past conversations into current context

---

## REQUIRED BEFORE STARTING

Ask the user for:

1. **TELEGRAM_BOT_TOKEN** — from @BotFather
2. **ALLOWED_CHAT_ID** — their Telegram chat ID (use @userinfobot)
3. **ANTHROPIC_API_KEY** — must already be configured for Claude Code
4. **OPENAI_API_KEY** *(optional)* — Whisper voice transcription
5. **GOOGLE_API_KEY** *(optional)* — Gemini for video analysis / cheap summarization
6. **KIE_AI_KEY** *(optional)* — image generation via Nano Banana 2

---

## BUILD STEPS

1. Create all project files from specs below
2. Write `.env` with collected credentials
3. `npm install`
4. `npm run build`
5. Create systemd service
6. `systemctl start claudeclaw`
7. Create agent files in `~/.claude/agents/`
8. Report success

---

## PROJECT FILES

### `package.json`

```json
{
  "name": "claudeclaw",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx src/index.ts"
  },
  "engines": { "node": ">=20" },
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.2.59",
    "better-sqlite3": "^11.0.0",
    "cron-parser": "^4.9.0",
    "grammy": "^1.31.0",
    "openai": "^6.25.0",
    "pino": "^9.0.0",
    "pino-pretty": "^11.0.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.13",
    "@types/node": "^22.19.13",
    "tsx": "^4.21.0",
    "typescript": "^5.9.3"
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
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

### `src/env.ts`

```typescript
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')

export function readEnvFile(keys?: string[], filePath?: string): Record<string, string> {
  const envPath = filePath ?? path.join(PROJECT_ROOT, '.env')
  try {
    const content = readFileSync(envPath, 'utf-8')
    const result: Record<string, string> = {}
    for (const line of content.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      const eqIdx = trimmed.indexOf('=')
      if (eqIdx === -1) continue
      const key = trimmed.slice(0, eqIdx).trim()
      let value = trimmed.slice(eqIdx + 1).trim()
      if ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1)
      }
      result[key] = value
    }
    return keys ? Object.fromEntries(keys.filter(k => k in result).map(k => [k, result[k]!])) : result
  } catch { return {} }
}
```

---

### `src/config.ts`

```typescript
import { readEnvFile } from './env.js'
import { fileURLToPath } from 'url'
import path from 'path'
import os from 'os'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export const PROJECT_ROOT = path.resolve(__dirname, '..')
export const STORE_DIR = path.join(PROJECT_ROOT, 'store')

const env = readEnvFile()

export const TELEGRAM_BOT_TOKEN = env['TELEGRAM_BOT_TOKEN'] ?? ''
export const ALLOWED_CHAT_ID = env['ALLOWED_CHAT_ID'] ?? ''
export const MAX_MESSAGE_LENGTH = 4096
export const TYPING_REFRESH_MS = 4000

const boolEnv = (k: string, d: boolean) => { const v = env[k]; return v === undefined ? d : v === 'true' || v === '1' }
const floatEnv = (k: string, d: number) => { const v = env[k]; if (!v) return d; const n = parseFloat(v); return isNaN(n) ? d : n }
const intEnv = (k: string, d: number) => { const v = env[k]; if (!v) return d; const n = parseInt(v, 10); return isNaN(n) ? d : n }

export const MEMORY_CONFIG = {
  ENABLE_AUTO_CHECKPOINT: boolEnv('ENABLE_AUTO_CHECKPOINT', true),
  ENABLE_DEEP_HISTORY: boolEnv('ENABLE_DEEP_HISTORY', true),
  ENABLE_MEMORY_DEBUG: boolEnv('ENABLE_MEMORY_DEBUG', false),

  THRESHOLD_WARN: floatEnv('MEMORY_THRESHOLD_WARN', 0.70),
  THRESHOLD_CHECKPOINT: floatEnv('MEMORY_THRESHOLD_CHECKPOINT', 0.80),
  THRESHOLD_NEW_CHAT: floatEnv('MEMORY_THRESHOLD_NEW_CHAT', 0.85),

  MAX_CONTEXT_TOKENS: intEnv('MEMORY_MAX_CONTEXT_TOKENS', 200000),
  MAX_DEEP_HISTORY_TOKENS: intEnv('MEMORY_MAX_DEEP_HISTORY_TOKENS', 2000),
  MAX_RETRIEVED_CHUNKS: intEnv('MEMORY_MAX_RETRIEVED_CHUNKS', 5),
  MAX_CHECKPOINT_CHARS: intEnv('MEMORY_MAX_CHECKPOINT_CHARS', 1500),
  HISTORY_KEEP_DAYS: intEnv('MEMORY_HISTORY_KEEP_DAYS', 30),

  CLAUDE_PROJECT_SLUG: env['CLAUDE_PROJECT_SLUG'] ?? '-root-claudeclaw',
  get CLAUDE_PROJECT_DIR(): string {
    return path.join(os.homedir(), '.claude', 'projects', this.CLAUDE_PROJECT_SLUG)
  },
}
```

---

### `src/logger.ts`

```typescript
import pino from 'pino'

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  transport: process.env.NODE_ENV !== 'production'
    ? { target: 'pino-pretty', options: { colorize: true } }
    : undefined,
})
```

---

### `src/db.ts`

```typescript
import Database from 'better-sqlite3'
import path from 'path'
import { mkdirSync } from 'fs'
import { STORE_DIR } from './config.js'

mkdirSync(STORE_DIR, { recursive: true })
export const db = new Database(path.join(STORE_DIR, 'claudeclaw.db'))
db.pragma('journal_mode = WAL')

export interface MemoryRow {
  id: number; chat_id: string; topic_key: string | null; content: string
  sector: 'semantic' | 'episodic' | 'procedural'; salience: number
  created_at: number; accessed_at: number; parent_topic: string | null; tags: string | null
}

export interface HistoryRow {
  id: number; chat_id: string; session_id: string | null
  role: 'user' | 'assistant'; content: string; content_hash: string; created_at: number
}

export interface ScheduledTask {
  id: string; chat_id: string; prompt: string; schedule: string
  next_run: number; last_run: number | null; last_result: string | null
  status: 'active' | 'paused'; created_at: number
}

export function initDatabase(): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS sessions (
      chat_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, updated_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memories (
      id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, topic_key TEXT,
      content TEXT NOT NULL, sector TEXT NOT NULL CHECK(sector IN ('semantic','episodic','procedural')),
      salience REAL NOT NULL DEFAULT 1.0, created_at INTEGER NOT NULL, accessed_at INTEGER NOT NULL,
      parent_topic TEXT DEFAULT NULL, tags TEXT DEFAULT NULL
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, content='memories', content_rowid='id');
    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
      INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content); END;
    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content);
      INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content); END;
    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, content) VALUES ('delete', old.id, old.content); END;
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
      id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, prompt TEXT NOT NULL, schedule TEXT NOT NULL,
      next_run INTEGER NOT NULL, last_run INTEGER, last_result TEXT,
      status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused')), created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status_next_run ON scheduled_tasks(status, next_run);
    CREATE TABLE IF NOT EXISTS conversation_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, session_id TEXT,
      role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
      content TEXT NOT NULL, content_hash TEXT NOT NULL, created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ch_chat_created ON conversation_history(chat_id, created_at DESC);
    CREATE VIRTUAL TABLE IF NOT EXISTS conversation_history_fts USING fts5(
      content, content='conversation_history', content_rowid='id');
    CREATE TRIGGER IF NOT EXISTS ch_ai AFTER INSERT ON conversation_history BEGIN
      INSERT INTO conversation_history_fts(rowid, content) VALUES (new.id, new.content); END;
    CREATE TRIGGER IF NOT EXISTS ch_ad AFTER DELETE ON conversation_history BEGIN
      INSERT INTO conversation_history_fts(conversation_history_fts, rowid, content)
        VALUES ('delete', old.id, old.content); END;
  `)
  for (const sql of [
    `ALTER TABLE memories ADD COLUMN parent_topic TEXT DEFAULT NULL`,
    `ALTER TABLE memories ADD COLUMN tags TEXT DEFAULT NULL`,
  ]) { try { db.exec(sql) } catch { /* exists */ } }
}

// Sessions
export const getSession = (chatId: string) =>
  db.prepare<[string], { session_id: string }>('SELECT session_id FROM sessions WHERE chat_id = ?').get(chatId)?.session_id ?? null
export const setSession = (chatId: string, sessionId: string) =>
  db.prepare('INSERT OR REPLACE INTO sessions (chat_id, session_id, updated_at) VALUES (?, ?, ?)').run(chatId, sessionId, Math.floor(Date.now() / 1000))
export const clearSession = (chatId: string) =>
  db.prepare('DELETE FROM sessions WHERE chat_id = ?').run(chatId)

// Memories
export function findSimilarMemory(chatId: string, content: string): boolean {
  return db.prepare<[string, string], { id: number }>(
    "SELECT id FROM memories WHERE chat_id = ? AND content LIKE ? LIMIT 1"
  ).get(chatId, `${content.slice(0, 80)}%`) != null
}

export function insertMemory(chatId: string, content: string, sector: 'semantic' | 'episodic' | 'procedural',
  topicKey?: string, parentTopic?: string, tags?: string[]): void {
  if (findSimilarMemory(chatId, content)) return
  const now = Math.floor(Date.now() / 1000)
  db.prepare('INSERT INTO memories (chat_id, topic_key, content, sector, salience, created_at, accessed_at, parent_topic, tags) VALUES (?, ?, ?, ?, 1.0, ?, ?, ?, ?)')
    .run(chatId, topicKey ?? null, content, sector, now, now, parentTopic ?? null, tags ? JSON.stringify(tags) : null)
}

export function touchMemories(ids: number[]): void {
  if (!ids.length) return
  const now = Math.floor(Date.now() / 1000)
  const stmt = db.prepare('UPDATE memories SET accessed_at = ?, salience = MIN(salience + 0.1, 5.0) WHERE id = ?')
  ids.forEach(id => stmt.run(now, id))
}

export const searchMemoriesFTS = (chatId: string, query: string, limit = 3): MemoryRow[] =>
  db.prepare<[string, string, number], MemoryRow>(
    `SELECT m.* FROM memories_fts fts JOIN memories m ON m.id = fts.rowid
     WHERE memories_fts MATCH ? AND m.chat_id = ? ORDER BY rank LIMIT ?`
  ).all(query, chatId, limit)

export const getRecentMemories = (chatId: string, limit = 5): MemoryRow[] =>
  db.prepare<[string, number], MemoryRow>('SELECT * FROM memories WHERE chat_id = ? ORDER BY accessed_at DESC LIMIT ?').all(chatId, limit)

export const getMemoriesForDisplay = (chatId: string, limit = 10): MemoryRow[] =>
  db.prepare<[string, number], MemoryRow>('SELECT * FROM memories WHERE chat_id = ? ORDER BY salience DESC, accessed_at DESC LIMIT ?').all(chatId, limit)

export function decayMemories(): void {
  const oneDayAgo = Math.floor(Date.now() / 1000) - 86400
  db.prepare("UPDATE memories SET salience = salience * 0.85 WHERE sector = 'episodic' AND created_at < ?").run(oneDayAgo)
  db.prepare("UPDATE memories SET salience = salience * 0.97 WHERE sector = 'semantic' AND created_at < ?").run(oneDayAgo)
  db.prepare('DELETE FROM memories WHERE salience < 0.2').run()
}

export const getMemoryCount = () =>
  (db.prepare<[], { count: number }>('SELECT COUNT(*) as count FROM memories').get()?.count ?? 0)

// Scheduled Tasks
export const createTask = (task: Omit<ScheduledTask, 'last_run' | 'last_result'>) =>
  db.prepare(`INSERT INTO scheduled_tasks (id, chat_id, prompt, schedule, next_run, last_run, last_result, status, created_at) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)`)
    .run(task.id, task.chat_id, task.prompt, task.schedule, task.next_run, task.status, task.created_at)
export const getAllTasks = (): ScheduledTask[] =>
  db.prepare<[], ScheduledTask>('SELECT * FROM scheduled_tasks ORDER BY created_at DESC').all()
export const getDueTasks = (): ScheduledTask[] =>
  db.prepare<[string, number], ScheduledTask>("SELECT * FROM scheduled_tasks WHERE status = ? AND next_run <= ?").all('active', Math.floor(Date.now() / 1000))
export const updateTaskAfterRun = (id: string, lastResult: string, nextRun: number) =>
  db.prepare('UPDATE scheduled_tasks SET last_run = ?, last_result = ?, next_run = ? WHERE id = ?').run(Math.floor(Date.now() / 1000), lastResult, nextRun, id)
export const setTaskStatus = (id: string, status: 'active' | 'paused') =>
  db.prepare('UPDATE scheduled_tasks SET status = ? WHERE id = ?').run(status, id)
export const deleteTask = (id: string) =>
  db.prepare('DELETE FROM scheduled_tasks WHERE id = ?').run(id)

// Conversation History (Layer 2)
export function saveHistoryEntry(chatId: string, sessionId: string | null, role: 'user' | 'assistant', content: string): void {
  const hash = content.slice(0, 64)
  if (db.prepare<[string, string], { id: number }>('SELECT id FROM conversation_history WHERE chat_id = ? AND content_hash = ? LIMIT 1').get(chatId, hash)) return
  db.prepare('INSERT INTO conversation_history (chat_id, session_id, role, content, content_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)')
    .run(chatId, sessionId ?? null, role, content, hash, Math.floor(Date.now() / 1000))
}

export function searchHistory(chatId: string, query: string, limit = 5): HistoryRow[] {
  const sanitized = query.replace(/[^a-zA-Zа-яёА-ЯЁ0-9\s]/g, ' ').trim()
    .split(/\s+/).filter(w => w.length > 3).slice(0, 6).map(w => `${w}*`).join(' ')
  if (!sanitized) return []
  try {
    return db.prepare<[string, string, number], HistoryRow>(
      `SELECT h.* FROM conversation_history_fts fts JOIN conversation_history h ON h.id = fts.rowid
       WHERE conversation_history_fts MATCH ? AND h.chat_id = ? ORDER BY rank LIMIT ?`
    ).all(sanitized, chatId, limit)
  } catch { return [] }
}

export const getRecentHistoryEntries = (chatId: string, limit = 10): HistoryRow[] =>
  db.prepare<[string, number], HistoryRow>('SELECT * FROM conversation_history WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?').all(chatId, limit)

export function saveCheckpoint(chatId: string, summary: string, topicKey: string): void {
  const now = Math.floor(Date.now() / 1000)
  db.prepare('DELETE FROM memories WHERE chat_id = ? AND topic_key = ?').run(chatId, topicKey)
  db.prepare(`INSERT INTO memories (chat_id, topic_key, content, sector, salience, created_at, accessed_at) VALUES (?, ?, ?, 'semantic', 5.0, ?, ?)`)
    .run(chatId, topicKey, summary, now, now)
}
```

---

### `src/memory.ts`

```typescript
import { readFileSync, readdirSync, statSync } from 'fs'
import path from 'path'
import { insertMemory, searchMemoriesFTS, getRecentMemories, touchMemories,
  decayMemories as dbDecayMemories, saveHistoryEntry, searchHistory, saveCheckpoint } from './db.js'
import { logger } from './logger.js'
import { MEMORY_CONFIG } from './config.js'

const SEMANTIC_PATTERN = /\b(my|i am|i'm|i prefer|remember|always|never|мой|моя|моё|я всегда|запомни|никогда|предпочитаю)\b/i
const NOISE_PATTERN = /^\[Voice transcribed\]:|^\[Photo |^\[Video |^\[Document |^(ок|хорошо|понял|ясно|отлично|спасибо|да|нет|ок$)/i
const API_KEY_PATTERN = /\b(sk-|AIza|Bearer\s)/
const RECALL_INTENT_PATTERN = /что мы решили|what did we decide|помнишь как|you said|мы обсуждали|earlier today|ранее|до этого|remind me|напомни|вспомни|ты говорил|ты писал|we talked about|we discussed/i

export const detectRecallIntent = (text: string) => RECALL_INTENT_PATTERN.test(text)

export async function buildMemoryContext(chatId: string, userMessage: string): Promise<string> {
  const results: Array<{ id: number; content: string; sector: string; topic_key?: string | null }> = []
  const seenTopicKeys = new Set<string>()

  const sanitized = userMessage.replace(/[^a-zA-Zа-яёА-ЯЁ0-9\s]/g, ' ').trim()
    .split(/\s+/).filter(w => w.length > 3).slice(0, 6).map(w => `${w}*`).join(' ')

  if (sanitized) {
    try {
      for (const row of searchMemoriesFTS(chatId, sanitized, 2)) {
        if (row.topic_key && seenTopicKeys.has(row.topic_key)) continue
        results.push({ id: row.id, content: row.content, sector: row.sector, topic_key: row.topic_key })
        if (row.topic_key) seenTopicKeys.add(row.topic_key)
      }
    } catch (err) { logger.warn({ err }, 'FTS search failed') }
  }

  for (const row of getRecentMemories(chatId, 3)) {
    if (results.find(r => r.id === row.id)) continue
    if (row.topic_key && seenTopicKeys.has(row.topic_key)) continue
    if (row.sector === 'semantic') {
      results.push({ id: row.id, content: row.content, sector: row.sector, topic_key: row.topic_key })
      if (row.topic_key) seenTopicKeys.add(row.topic_key)
    }
  }

  if (!results.length) return ''
  touchMemories(results.map(r => r.id))
  return `[Memory]\n${results.slice(0, 3).map(r => `- ${r.content.slice(0, 80)}`).join('\n')}`
}

export async function saveConversationTurn(chatId: string, userMsg: string, _assistantMsg: string): Promise<void> {
  if (userMsg.length <= 20 || userMsg.startsWith('/')) return
  if (NOISE_PATTERN.test(userMsg) || API_KEY_PATTERN.test(userMsg)) return
  const compressed = userMsg.replace(/\[Voice transcribed\]:\s*/i, '').replace(/\s+/g, ' ').trim().slice(0, 120)
  if (SEMANTIC_PATTERN.test(userMsg)) {
    insertMemory(chatId, compressed, 'semantic')
  } else if (userMsg.length > 50) {
    insertMemory(chatId, compressed, 'episodic')
  }
}

export async function saveMessageToHistory(chatId: string, sessionId: string | null, userMsg: string, assistantMsg: string): Promise<void> {
  if (!MEMORY_CONFIG.ENABLE_DEEP_HISTORY) return
  if (userMsg.startsWith('/') || NOISE_PATTERN.test(userMsg) || API_KEY_PATTERN.test(userMsg)) return
  const maxChars = MEMORY_CONFIG.MAX_DEEP_HISTORY_TOKENS * 4
  if (userMsg.length > 20) saveHistoryEntry(chatId, sessionId, 'user', userMsg.slice(0, maxChars))
  if (assistantMsg?.length > 20) saveHistoryEntry(chatId, sessionId, 'assistant', assistantMsg.slice(0, maxChars))
}

export async function buildDeepHistoryContext(chatId: string, query: string): Promise<string> {
  const results = searchHistory(chatId, query, MEMORY_CONFIG.MAX_RETRIEVED_CHUNKS)
  if (!results.length) return ''
  const maxChars = MEMORY_CONFIG.MAX_DEEP_HISTORY_TOKENS * 4
  let total = 0
  const lines = ['[Conversation History — relevant past exchanges]']
  for (const row of results) {
    const entry = `${row.role === 'user' ? 'User' : 'Assistant'}: ${row.content.slice(0, 200)}`
    if (total + entry.length > maxChars) break
    lines.push(entry)
    total += entry.length
  }
  return lines.join('\n')
}

export function checkContextUsage(): number {
  try {
    const files = readdirSync(MEMORY_CONFIG.CLAUDE_PROJECT_DIR)
      .filter(f => f.endsWith('.jsonl'))
      .map(f => ({ path: path.join(MEMORY_CONFIG.CLAUDE_PROJECT_DIR, f), mtime: statSync(path.join(MEMORY_CONFIG.CLAUDE_PROJECT_DIR, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime)
    if (!files.length) return 0
    const lines = readFileSync(files[0]!.path, 'utf-8').trim().split('\n').filter(Boolean)
    for (let i = lines.length - 1; i >= 0; i--) {
      try {
        const p = JSON.parse(lines[i]!) as Record<string, unknown>
        const u = p['usage'] as Record<string, unknown> | undefined
        if (u?.['cache_read_input_tokens'] !== undefined)
          return Number(u['cache_read_input_tokens']) / MEMORY_CONFIG.MAX_CONTEXT_TOKENS
      } catch { continue }
    }
    return 0
  } catch { return 0 }
}

export function createAutoCheckpoint(chatId: string): void {
  try {
    const files = readdirSync(MEMORY_CONFIG.CLAUDE_PROJECT_DIR)
      .filter(f => f.endsWith('.jsonl'))
      .map(f => ({ path: path.join(MEMORY_CONFIG.CLAUDE_PROJECT_DIR, f), mtime: statSync(path.join(MEMORY_CONFIG.CLAUDE_PROJECT_DIR, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime)
    if (!files.length) return
    const lines = readFileSync(files[0]!.path, 'utf-8').trim().split('\n').filter(Boolean)
    const msgs: string[] = []
    for (let i = lines.length - 1; i >= Math.max(0, lines.length - 20); i--) {
      try {
        const p = JSON.parse(lines[i]!) as Record<string, unknown>
        if (p['type'] === 'assistant') {
          const blocks = (p['message'] as Record<string, unknown>)?.['content'] as Array<Record<string, unknown>> | undefined
          if (blocks) for (const b of blocks) if (b['type'] === 'text') { msgs.unshift(String(b['text']).slice(0, 200)); break }
        }
      } catch { continue }
      if (msgs.length >= 3) break
    }
    if (!msgs.length) return
    const today = new Date().toISOString().slice(0, 10)
    saveCheckpoint(chatId, `[Auto-checkpoint]\nKey facts: ${msgs.join(' | ').slice(0, MEMORY_CONFIG.MAX_CHECKPOINT_CHARS)}`, `checkpoint_${today}`)
    logger.info({ chatId }, 'Auto-checkpoint saved')
  } catch (err) { logger.warn({ err }, 'Auto-checkpoint failed') }
}

export function runDecaySweep(): void {
  try { dbDecayMemories(); logger.info('Memory decay sweep complete') }
  catch (err) { logger.warn({ err }, 'Decay sweep failed') }
}
```

---

### `src/agent.ts`

```typescript
import { query } from '@anthropic-ai/claude-agent-sdk'
import type { SDKMessage } from '@anthropic-ai/claude-agent-sdk'
import { PROJECT_ROOT, TYPING_REFRESH_MS } from './config.js'
import { logger } from './logger.js'

export async function runAgent(
  message: string, sessionId?: string, onTyping?: () => void
): Promise<{ text: string | null; newSessionId?: string }> {
  let text: string | null = null
  let newSessionId: string | undefined
  const typingInterval = onTyping ? setInterval(onTyping, TYPING_REFRESH_MS) : null
  try {
    const { CLAUDECODE: _stripped, ...cleanEnv } = process.env as Record<string, string>
    const events = query({
      prompt: message,
      options: {
        cwd: PROJECT_ROOT, resume: sessionId,
        settingSources: ['project', 'user'],
        permissionMode: 'default', env: cleanEnv,
      },
    })
    for await (const event of events as AsyncGenerator<SDKMessage>) {
      if (event.type === 'system' && event.subtype === 'init') {
        newSessionId = event.session_id
      } else if (event.type === 'result') {
        text = event.subtype === 'success' ? event.result
          : `Error: ${(event as { errors?: string[] }).errors?.join('; ') ?? 'Agent error'}`
      }
    }
  } finally { if (typingInterval) clearInterval(typingInterval) }
  return { text, newSessionId }
}
```

---

### `src/media.ts`

```typescript
import { createWriteStream, mkdirSync, readdirSync, statSync, unlinkSync, createReadStream } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import https from 'https'
import OpenAI from 'openai'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')
export const UPLOADS_DIR = path.join(PROJECT_ROOT, 'workspace', 'inbox')
mkdirSync(UPLOADS_DIR, { recursive: true })

const httpsGet = (url: string): Promise<Buffer> => new Promise((resolve, reject) => {
  https.get(url, res => {
    const chunks: Buffer[] = []
    res.on('data', (c: Buffer) => chunks.push(c))
    res.on('end', () => resolve(Buffer.concat(chunks)))
    res.on('error', reject)
  }).on('error', reject)
})

export async function downloadMedia(botToken: string, fileId: string, originalFilename?: string): Promise<string> {
  const meta = JSON.parse((await httpsGet(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`)).toString()) as { result?: { file_path?: string } }
  const filePath = meta.result?.file_path
  if (!filePath) throw new Error('Could not get file path from Telegram')
  const data = await httpsGet(`https://api.telegram.org/file/bot${botToken}/${filePath}`)
  const ext = path.extname(filePath) || path.extname(originalFilename ?? '') || ''
  const localPath = path.join(UPLOADS_DIR, `${Date.now()}_${(originalFilename ? path.basename(originalFilename, ext) : 'file').replace(/[^a-zA-Z0-9._-]/g, '-')}${ext}`)
  await new Promise<void>((resolve, reject) => {
    const ws = createWriteStream(localPath)
    ws.write(data, err => { if (err) return reject(err); ws.end(); ws.on('finish', resolve); ws.on('error', reject) })
  })
  return localPath
}

export const buildPhotoMessage = (localPath: string, caption?: string) =>
  [`[Photo attached: ${localPath}]`, caption && `Caption: ${caption}`, 'Please analyze this image.'].filter(Boolean).join('\n')

export const buildDocumentMessage = (localPath: string, filename: string, caption?: string) =>
  [`[Document attached: ${localPath}]`, `Filename: ${filename}`, caption && `Caption: ${caption}`, 'Please read and summarize this document.'].filter(Boolean).join('\n')

export const buildVideoMessage = (localPath: string, caption?: string) => {
  const parts = [`[Video attached: ${localPath}]`]
  if (caption) parts.push(`Caption: ${caption}`)
  const k = process.env.GOOGLE_API_KEY
  if (k) parts.push(`Analyze with Gemini (key: ${k}). Upload to googleapis.com/upload/v1beta/files, then call gemini-2.5-flash:generateContent.`)
  else parts.push('Report the file path to user.')
  return parts.join('\n')
}

export async function transcribeVoice(localPath: string): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) throw new Error('OPENAI_API_KEY not set')
  return (await new OpenAI({ apiKey }).audio.transcriptions.create({ file: createReadStream(localPath), model: 'whisper-1' })).text
}

export function cleanupOldUploads(maxAgeMs = 86400000): void {
  try {
    const now = Date.now()
    readdirSync(UPLOADS_DIR).forEach(f => {
      const fp = path.join(UPLOADS_DIR, f)
      try { if (now - statSync(fp).mtimeMs > maxAgeMs) unlinkSync(fp) } catch { /* ignore */ }
    })
  } catch { /* ignore */ }
}
```

---

### `src/scheduler.ts`

```typescript
import CronParser from 'cron-parser'
import { getDueTasks, updateTaskAfterRun } from './db.js'
import { runAgent } from './agent.js'
import { logger } from './logger.js'

export type Sender = (chatId: string, text: string) => Promise<void>

export const computeNextRun = (cron: string) =>
  Math.floor(CronParser.parseExpression(cron).next().toDate().getTime() / 1000)

export function initScheduler(send: Sender): void {
  setInterval(() => runDueTasks(send).catch(err => logger.error({ err }, 'Scheduler poll error')), 60000)
  logger.info('Scheduler initialized')
}

export async function runDueTasks(send: Sender): Promise<void> {
  for (const task of getDueTasks()) {
    logger.info({ taskId: task.id }, 'Running scheduled task')
    try {
      await send(task.chat_id, `Running: ${task.prompt.slice(0, 80)}...`)
      const { text } = await runAgent(task.prompt)
      updateTaskAfterRun(task.id, text ?? '(no result)', computeNextRun(task.schedule))
      await send(task.chat_id, (text ?? '(no result)').slice(0, 4000))
    } catch (err) {
      logger.error({ err, taskId: task.id }, 'Task failed')
      updateTaskAfterRun(task.id, `Error: ${String(err)}`, computeNextRun(task.schedule))
    }
  }
}
```

---

### `src/schedule-cli.ts`

```typescript
import { randomUUID } from 'crypto'
import CronParser from 'cron-parser'
import { initDatabase, createTask, getAllTasks, deleteTask, setTaskStatus, type ScheduledTask } from './db.js'
import { computeNextRun } from './scheduler.js'

initDatabase()
const [, , cmd, ...args] = process.argv

const validateCron = (e: string) => { try { CronParser.parseExpression(e); return true } catch { return false } }
const fmt = (t: ScheduledTask) => `ID: ${t.id}\nStatus: ${t.status}\nPrompt: ${t.prompt.slice(0, 60)}\nSchedule: ${t.schedule}\nNext: ${new Date(t.next_run * 1000).toLocaleString()}\n---`

switch (cmd) {
  case 'create': {
    const [prompt, schedule, chatId] = args
    if (!prompt || !schedule || !chatId) { console.error('Usage: create "prompt" "cron" chat_id'); process.exit(1) }
    if (!validateCron(schedule)) { console.error(`Invalid cron: ${schedule}`); process.exit(1) }
    const id = randomUUID(); const now = Math.floor(Date.now() / 1000)
    createTask({ id, chat_id: chatId, prompt, schedule, next_run: computeNextRun(schedule), status: 'active', created_at: now })
    console.log(`Created: ${id}\nNext: ${new Date(computeNextRun(schedule) * 1000).toLocaleString()}`)
    break
  }
  case 'list': { const t = getAllTasks(); console.log(t.length ? t.map(fmt).join('\n') : 'No tasks.'); break }
  case 'delete': { if (!args[0]) process.exit(1); deleteTask(args[0]); console.log('Deleted.'); break }
  case 'pause': { if (!args[0]) process.exit(1); setTaskStatus(args[0], 'paused'); console.log('Paused.'); break }
  case 'resume': { if (!args[0]) process.exit(1); setTaskStatus(args[0], 'active'); console.log('Resumed.'); break }
  default: console.log('Commands: create "prompt" "cron" chat_id | list | delete <id> | pause <id> | resume <id>')
}
```

---

### `src/bot.ts`

This is the largest file. It contains:
- `formatForTelegram()` — Markdown → HTML conversion for Telegram
- `splitMessage()` — splits long messages at newlines
- `isAuthorised()` — chat ID whitelist check
- `handleMessage()` — main handler: builds memory context, injects deep history if recall intent detected, calls `runAgent()`, saves to both memory layers, sends response, runs auto-checkpoint
- `createBot()` — all bot commands and message handlers

**Commands:** `/start`, `/chatid`, `/newchat`, `/forget`, `/checkpoint`, `/convolife`, `/recall <query>`, `/memory`, `/schedule`

**Message handlers:** `message:text`, `message:photo`, `message:document`, `message:video`, `message:video_note`, `message:voice`

Create this file with full implementation. Key logic in `handleMessage`:

```typescript
// Skip memory for short/trivial messages
const skipMemory = rawText.length < 20 || /^(\d+|ок|да|нет|хорошо|понял|спасибо|yes|no|ok|sure|got it|thanks)$/i.test(rawText.trim())

// Layer 1: compressed summaries
const memCtx = skipMemory ? '' : await buildMemoryContext(chatId, rawText)

// Layer 2: inject deep history only on recall intent
let deepCtx = ''
if (!skipMemory && MEMORY_CONFIG.ENABLE_DEEP_HISTORY && detectRecallIntent(rawText)) {
  deepCtx = await buildDeepHistoryContext(chatId, rawText)
}

// Compose: [Deep History] + [Memory] + user text
let message = rawText
if (memCtx) message = `${memCtx}\n\n${message}`
if (deepCtx) message = `${deepCtx}\n\n${message}`

// Run agent, save session, save to both memory layers
// After response: check context usage, auto-checkpoint if > threshold
```

`formatForTelegram` converts Markdown to HTML (`**bold**` → `<b>`, `` `code` `` → `<code>`, etc.) with HTML escaping and code block preservation.

---

### `src/index.ts`

```typescript
import { writeFileSync, readFileSync, unlinkSync, mkdirSync } from 'fs'
import path from 'path'
import { initDatabase } from './db.js'
import { createBot } from './bot.js'
import { runDecaySweep } from './memory.js'
import { cleanupOldUploads } from './media.js'
import { initScheduler } from './scheduler.js'
import { STORE_DIR, TELEGRAM_BOT_TOKEN } from './config.js'
import { logger } from './logger.js'

const PID_FILE = path.join(STORE_DIR, 'claudeclaw.pid')

function acquireLock() {
  mkdirSync(STORE_DIR, { recursive: true })
  try {
    const pid = parseInt(readFileSync(PID_FILE, 'utf-8').trim(), 10)
    if (!isNaN(pid)) try { process.kill(pid, 0); process.kill(pid, 'SIGTERM') } catch { /* stale */ }
  } catch { /* no file */ }
  writeFileSync(PID_FILE, String(process.pid))
}

async function main() {
  console.log(' ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗\n██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝\n██║     ██║     ███████║██║   ██║██║  ██║█████╗\n██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝\n╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗\n ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝╚══════╝')
  if (!TELEGRAM_BOT_TOKEN) { console.error('TELEGRAM_BOT_TOKEN not set'); process.exit(1) }
  acquireLock()
  initDatabase()
  runDecaySweep()
  setInterval(runDecaySweep, 86400000)
  cleanupOldUploads()
  const { bot, sendToChat } = createBot()
  initScheduler(sendToChat)
  const shutdown = async (sig: string) => { logger.info({ sig }, 'Shutdown'); try { unlinkSync(PID_FILE) } catch {}; bot.stop(); process.exit(0) }
  process.on('SIGINT', () => void shutdown('SIGINT'))
  process.on('SIGTERM', () => void shutdown('SIGTERM'))
  await bot.start()
}

main().catch(err => { logger.error({ err }, 'Fatal'); process.exit(1) })
```

---

## DIRECTORY STRUCTURE

```
claudeclaw/
├── src/
│   ├── index.ts, bot.ts, agent.ts, config.ts
│   ├── db.ts, memory.ts, media.ts
│   ├── scheduler.ts, schedule-cli.ts
│   ├── env.ts, logger.ts
├── scripts/
│   └── notify.sh
├── specs/agents/README.md
├── workspace/
│   ├── inbox/
│   ├── tmp/
│   └── output/
│       ├── notes/{YouTube,TikTok,Instagram}/
│       ├── reports/, images/, scripts/, exports/, presentations/
│       └── agents/
├── store/          (auto-created)
├── CLAUDE.md
├── package.json, tsconfig.json, .env
```

---

## `.env`

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ALLOWED_CHAT_ID=your_chat_id

# Optional
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIzaSy...
KIE_AI_KEY=...
```

---

## `scripts/notify.sh`

```bash
#!/usr/bin/env bash
PROJECT_ROOT="$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"
ENV_FILE="$PROJECT_ROOT/.env"
BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
CHAT_ID=$(grep '^ALLOWED_CHAT_ID=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
[ -z "${1:-}" ] && { echo "Usage: notify.sh \"message\"" >&2; exit 1; }
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":\"${1}\"}" > /dev/null
```

```bash
chmod +x scripts/notify.sh
```

---

## SYSTEMD SERVICE

`/etc/systemd/system/claudeclaw.service`:

```ini
[Unit]
Description=ClaudeClaw AI Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/claudeclaw
ExecStart=/usr/bin/node /root/claudeclaw/dist/index.js
EnvironmentFile=/root/claudeclaw/.env
Environment=NODE_ENV=production
Environment=HOME=/root
Environment=PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable claudeclaw && systemctl start claudeclaw
```

---

## AGENTS (`~/.claude/agents/`)

```bash
mkdir -p ~/.claude/agents
```

### `youtube-analyzer.md`

```markdown
---
name: youtube-analyzer
description: Specialized agent for analyzing a single YouTube video. Used by ClaudeClaw orchestrator in agent teams. Takes a YouTube URL, calls n8n webhook, saves to workspace + Obsidian, returns structured summary.
tools: Bash, Read, Write, Edit, Glob, Grep
---

Analyze one YouTube video and return structured result.

## Pipeline
1. Call webhook: POST https://YOUR_N8N_HOST/webhook/youtube_claudeclaw  body: {"url":"URL"}
2. Parse: title, channel, summary, keyPoints[], takeaways[], actionIdeas[], confidence
3. Save: workspace/output/notes/YouTube/YYYY-MM-DD-{slug}.md
4. Save: ~/obsidian-vault/YouTube/YYYY-MM-DD-{slug}.md (YAML frontmatter + [[channel]] wikilinks)
5. Check/create: ~/obsidian-vault/YouTube/Authors/{channel}.md
6. If task_id: workspace/output/agents/{task_id}/youtube-analyzer-{slug}.md

## Return JSON
{"url":"...","title":"...","channel":"...","summary":"...(300 chars)...","keyPoints":[...],"takeaways":[...],"actionIdeas":[...],"file":"..."}

## Rules
- Always curl directly. Date: YYYY-MM-DD. Slug: lowercase-hyphens max 60 chars.
```

### `tiktok-analyzer.md`

```markdown
---
name: tiktok-analyzer
description: Specialized agent for analyzing a single TikTok video. Used by ClaudeClaw orchestrator in agent teams. Takes a TikTok URL, calls n8n webhook, saves to workspace + Obsidian, returns structured summary.
tools: Bash, Read, Write, Edit, Glob, Grep
---

Analyze one TikTok video and return structured result.

## Pipeline
1. Call webhook: POST https://YOUR_N8N_HOST/webhook/tiktokclaude  body: {"url":"URL"}
2. Parse: title, channel, summary, keyPoints[], takeaways[], actionIdeas[], confidence
3. Save: workspace/output/notes/TikTok/YYYY-MM-DD-{slug}.md
4. Save: ~/obsidian-vault/TikTok/YYYY-MM-DD-{slug}.md + Authors/{channel}.md
5. If task_id: workspace/output/agents/{task_id}/tiktok-analyzer-{slug}.md

## Return JSON
{"url":"...","title":"...","channel":"...","summary":"...","keyPoints":[...],"takeaways":[...],"actionIdeas":[...],"file":"..."}

## Rules: Always curl directly. Date: YYYY-MM-DD. Slug: lowercase-hyphens max 60 chars.
```

### `instagram-analyzer.md`

```markdown
---
name: instagram-analyzer
description: Specialized agent for analyzing a single Instagram Reel. Used by ClaudeClaw orchestrator in agent teams. Takes an Instagram Reel URL, calls n8n webhook, saves to workspace + Obsidian, returns structured summary.
tools: Bash, Read, Write, Edit, Glob, Grep
---

Analyze one Instagram Reel and return structured result.

## Pipeline
1. Call webhook: POST https://YOUR_N8N_HOST/webhook/analyze_instagram_video  body: {"url":"URL"}
2. Parse: title, channel, summary, keyPoints[], takeaways[], actionIdeas[], confidence
3. Save: workspace/output/notes/Instagram/YYYY-MM-DD-{slug}.md
4. Save: ~/obsidian-vault/Instagram/YYYY-MM-DD-{slug}.md + Authors/{channel}.md
5. If task_id: workspace/output/agents/{task_id}/instagram-analyzer-{slug}.md

## Return JSON
{"url":"...","title":"...","channel":"...","summary":"...","keyPoints":[...],"takeaways":[...],"actionIdeas":[...],"file":"..."}

## Rules: Always curl. If no title — generate from summary. Date: YYYY-MM-DD. Slug: max 60 chars.
```

### `content-writer.md`

```markdown
---
name: content-writer
description: Specialized agent for generating content for ONE platform (Threads, Instagram, or Reels). Used by ClaudeClaw orchestrator in agent teams. Takes platform + topic + context, returns formatted content variants.
tools: Bash, Read
---

Write content for ONE platform at a time.

Input: platform (threads|instagram|reels), topic, context

## Output
- Threads: 3 post variants. Hook + body + CTA. Max 500 chars each.
- Instagram: 2 caption variants. Emotional hook + value + 15-20 hashtags.
- Reels: Script with hook (first 3 sec) + bullet points + CTA. Max 60 sec.

## Rules
- Match user's language (default Russian). Direct tone, no fluff. Concrete hooks with numbers or provocative questions. Always return multiple variants.
```

---

## `CLAUDE.md`

```markdown
# ClaudeClaw

You are a personal AI assistant, accessible via Telegram.

## Personality
- No em dashes. Ever.
- No AI clichés ("Certainly!", "Great question!", "I'd be happy to", "As an AI")
- No sycophancy. No excessive apologies.
- Don't narrate what you're about to do. Just do it.

## Communication Style
- Language: match the user's language
- Tone: direct, no fluff
- Give result first, explanation only if asked
- No "maybe", "perhaps", "you could try"

## Your Job
Execute. Don't explain plans. If clarification needed, ask ONE short question.

## Your Environment
- Tools: Bash, file system, web search, all MCP servers
- Project root: directory where CLAUDE.md lives
- Obsidian vault: ~/obsidian-vault

## n8n Workflows
CRITICAL: Do NOT use social_media_analyst Task agent — it hallucinates. Use curl directly.

Webhooks (replace with your n8n host):
- YouTube:   POST https://YOUR_N8N_HOST/webhook/youtube_claudeclaw
- TikTok:    POST https://YOUR_N8N_HOST/webhook/tiktokclaude
- Instagram: POST https://YOUR_N8N_HOST/webhook/analyze_instagram_video

All accept: {"url": "VIDEO_URL"}

## Agent Teams
Agents in ~/.claude/agents/: youtube-analyzer, tiktok-analyzer, instagram-analyzer, content-writer

Triggers:
- YouTube URL → youtube-analyzer
- TikTok URL → tiktok-analyzer
- Instagram Reel URL → instagram-analyzer
- Multiple URLs → run all needed agents in parallel
- "content for all platforms" → content-writer x3 in parallel (threads + instagram + reels)

## Special Commands

### convolife
1. Find latest JSONL in ~/.claude/projects/ (project slug dir)
2. Get last cache_read_input_tokens value
3. Report: "Context: XX% used — ~XXk tokens remaining"

### checkpoint
Save 3-5 bullet summary to memories table: sector='semantic', salience=5.0, topic_key=checkpoint_YYYY_MM_DD

## Message Format
- Tight, readable responses
- Progress update via scripts/notify.sh only if task >30 sec or 3+ tool calls

## Workspace
workspace/inbox/        — files from Telegram
workspace/output/
  notes/{YouTube,TikTok,Instagram}/
  reports/, images/, scripts/, exports/, presentations/
  agents/{task_id}/     — agent team artifacts
workspace/tmp/          — temp files
```

---

## LAUNCH COMMANDS

```bash
npm install && npm run build

# Test run (no systemd)
npm start

# Production
systemctl daemon-reload && systemctl enable claudeclaw && systemctl start claudeclaw
journalctl -u claudeclaw -f

# After code changes
npm run build && systemctl restart claudeclaw

# Schedule a task
node /root/claudeclaw/dist/schedule-cli.js create "your prompt" "0 9 * * *" CHAT_ID
```

---

## VERIFICATION

Send to the bot:
1. `/start` → should reply with welcome
2. `hello` → should reply via Claude Code
3. `/convolife` → should show context usage
4. `/chatid` → should show your chat ID

---

## TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Bot not responding | `systemctl status claudeclaw` + `journalctl -u claudeclaw -n 50` |
| Claude Code not found | `which claude` — check PATH in systemd service |
| TypeScript build errors | `npx tsc --noEmit` for details; `npm install` |
| Agents not working | Check `~/.claude/agents/` files exist; check n8n webhook URLs |
| CLAUDECODE error | Normal — stripped in `agent.ts` via `cleanEnv` |

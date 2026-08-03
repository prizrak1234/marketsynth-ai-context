---
tags: [gemini, memory, sqlite, obsidian, layered-memory]
date: 2026-04-18
type: note
---

# Шаг 6: Гибридная память (SQLite + agent-memory.md + Obsidian)

Три слоя памяти, которые выживают между сессиями и не накапливают противоречия.

## Prerequisites

- Шаг 5 выполнен (бот работает с медиа)
- SQLite (better-sqlite3) установлен
- Путь к Obsidian vault: `~/obsidian-vault/` (опционально)

## Архитектура памяти

```
Layer 1 (episodic)  — SQLite: history, sessions, компактные сводки
Layer 2 (semantic)  — ~/obsidian-vault/GeminiClaw/agent-memory.md: факты, предпочтения, паттерны
Layer 3 (deep)      — ~/obsidian-vault/: полный vault, поиск через grep
```

**Scopes (область применения записей):**
- `user` — факты о пользователе (постоянно)
- `project` — данные о конкретных проектах (постоянно)
- `session` — заметки текущей сессии (30 дней)
- `team` — общие паттерны и правила (постоянно)

## Для зрителей без Obsidian

Если у тебя ещё нет Obsidian — создай базовую структуру:

```bash
mkdir -p ~/obsidian-vault/GeminiClaw
mkdir -p ~/obsidian-vault/Sessions
mkdir -p ~/obsidian-vault/Inbox
mkdir -p ~/obsidian-vault/Notes

# Создай файл памяти агента
cat > ~/obsidian-vault/GeminiClaw/agent-memory.md << 'EOF'
# Agent Memory

Long-term facts, decisions, and stable preferences.

## Entries

EOF
```

Obsidian — просто папка с markdown-файлами. Gemini читает их как обычный текст через grep или cat.

## Промпт для Gemini CLI

```text
Implement a 3-layer hybrid memory system for GeminiClaw.

## Layer 1: SQLite episodic memory
File: store/geminiclaw.db
Tables to create:

```sql
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'session',       -- user | project | session | team
  topic_key TEXT,                               -- unique key for deduplication
  content TEXT NOT NULL,
  salience REAL DEFAULT 1.0,                   -- importance 0..5
  decay_rate REAL DEFAULT 0.97,                -- per-day decay multiplier
  superseded_at INTEGER,                        -- null = active; unix timestamp = replaced
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  expires_at INTEGER                            -- null = permanent
);

CREATE TABLE IF NOT EXISTS sessions (
  chat_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  compact_count INTEGER DEFAULT 0,             -- incremented on each /compact
  last_compact_at INTEGER,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);
```

## Layer 2: agent-memory.md (semantic facts)
File: ~/obsidian-vault/GeminiClaw/agent-memory.md

Entry format:
```
### YYYY-MM-DD - Title
- Scope: user | project | session | team
- Content: [fact or preference]
- Source: user | task | observation
- Expires: permanent | YYYY-MM-DD
```

Rules:
- Before writing a new entry, search for existing entries on the same topic (topic_key match or keyword grep)
- If found, supersede old entry: set superseded_at = NOW(), then write new entry
- Never accumulate contradictions — always replace on same topic_key
- API keys, tokens, passwords must NEVER be saved to memory

## Layer 3: Obsidian vault (deep search)
- Use grep to search vault: grep -ril "QUERY" ~/obsidian-vault/ --include="*.md"
- Only when agent explicitly needs deeper context from vault
- Do not load entire vault into every prompt

## Memory functions to implement in src/memory.ts

### saveMemory(chatId, content, options)
- options: scope, topicKey, salience, decayRate, expiresInDays
- If topicKey exists in DB with same scope: set superseded_at on old record
- API key sanitization: reject if content matches /[A-Za-z0-9_-]{32,}/ or common key patterns
- normalizeRelativeDates: replace "сегодня"/"вчера"/"на прошлой неделе" with absolute YYYY-MM-DD dates

### getRelevantMemories(chatId, query): string[]
- Fetch active memories for chatId (superseded_at IS NULL, expires_at > NOW() or NULL)
- Apply salience decay: effective_salience = salience * (decay_rate ^ days_since_created)
- Sort by effective_salience DESC
- Return top 10 as text array

### buildContextPrefix(chatId, userMessage): string
- Call getRelevantMemories
- If relevant memories found, prepend to prompt:
  ```
  [Memory context]
  - MEMORY_1
  - MEMORY_2

  [User message]
  USER_MESSAGE
  ```

### saveSessionNote(chatId, content)
- Save to ~/obsidian-vault/Sessions/YYYY-MM-DD-geminiclaw-{chatId_short}.md
- Append if file exists for today, create new otherwise

### vaultSearch(query): string[]
- Run: grep -ril "QUERY" ~/obsidian-vault/ --include="*.md" | head -5
- For each file found, read first 50 lines
- Return array of relevant snippets

## Decay policy
- semantic scope (user, project, team): decay_rate = 0.97/day
- episodic scope (session): decay_rate = 0.85/day
- Permanent entries (scope=user, no expires_at): never decayed

## Memory write rules
- New entry supersedes old on same topic_key
- Scope=session entries auto-expire after 30 days (set expires_at = created_at + 30*86400)
- Scope=user/project/team: permanent unless explicitly deleted

## Update bot.ts
- In runGemini wrapper: call buildContextPrefix(chatId, message) before spawning
- Inject context prefix into the prompt
- Handle /recall command: search memories + vault, return formatted results
- Handle /memory command: show top 10 active memories for chat_id

## Update GEMINI.md with memory protocol
Add section:
```
## Memory Protocol
- Before thematic answers: check agent-memory.md if topic is known
- After significant tasks: update agent-memory.md with new facts
- Use vault search for deep context: grep -ril "topic" ~/obsidian-vault/
- Never save: API keys, tokens, passwords, PII
- Replace stale entries on same topic instead of accumulating
```
```

## После генерации

```bash
npm run build
pm2 restart geminiclaw
```

Проверка:

```bash
# Убедись что таблица создана
sqlite3 ~/GeminiClaw/store/geminiclaw.db ".tables"
# Должна вернуть: memories  sessions
```

## Troubleshooting

**SQLite лочится при параллельных запросах**
`better-sqlite3` синхронный — это нормально. Очередь сообщений в bot.ts гарантирует, что операции выполняются последовательно.

**agent-memory.md растёт бесконтрольно**
Запусти `/dream` (консолидация памяти) раз в неделю. Dream удаляет дубликаты и истёкшие записи.

**Контекст памяти слишком большой — Gemini получает огромный префикс**
Ограничь `getRelevantMemories` 10 записями и применяй decay — записи с низким effective_salience не попадут в контекст.

## После этого шага

- [ ] `sqlite3 store/geminiclaw.db ".tables"` возвращает `memories sessions`
- [ ] `~/obsidian-vault/GeminiClaw/agent-memory.md` существует
- [ ] Бот помнит факты между сессиями
- [ ] /recall работает
- [ ] /memory показывает активные воспоминания
- [ ] API-ключи не сохраняются в память (sanitization)

Следующий шаг: [[07_ADVANCED_ARCH]]

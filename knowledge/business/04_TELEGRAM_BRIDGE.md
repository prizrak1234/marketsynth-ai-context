---
tags: [gemini, telegram, bridge, grammy, typescript]
date: 2026-04-18
type: note
---

# Шаг 4: Telegram мост

Строим бота на grammY, который пробрасывает сообщения в Gemini CLI через `spawn`.

## Prerequisites

- Шаг 3 выполнен (проект инициализирован, зависимости установлены)
- `.env` содержит `TELEGRAM_BOT_TOKEN` и `ALLOWED_CHAT_ID`
- Gemini CLI авторизован

## Промпт для Gemini CLI

Находясь в папке `~/GeminiClaw`, отправь этот промпт в Gemini CLI:

```text
Build a production-ready Telegram bot that bridges user messages to Gemini CLI.

## Stack
- Framework: grammY (TypeScript)
- Runtime: Node.js 22, CommonJS modules
- Process manager: PM2 via ecosystem.config.js
- Config: dotenv, all secrets in .env

## Architecture
Every Telegram message spawns a child process: `gemini -p "USER_MESSAGE"`.
Do NOT use a long-lived gemini session — spawn fresh for each message.
Session continuity is handled via SQLite session_id injection into the prompt.

## .env variables (already created, do not overwrite)
- TELEGRAM_BOT_TOKEN — Telegram bot token
- ALLOWED_CHAT_ID — whitelist of allowed chat IDs (comma-separated for multiple users)

## Security
- Check ctx.chat.id against ALLOWED_CHAT_ID at the very start of every handler.
- If the chat ID is not in the whitelist, silently return — do not reply.
- Never log the full message content to stdout in production.

## Files to create or update

### src/env.ts
- Load .env with dotenv
- Export typed env object with required() validator
- Fields: TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID (split by comma into string[])

### src/gemini.ts
- Function: runGemini(prompt: string, sessionId?: string): Promise<string>
- Use child_process.spawn to run: gemini -p "PROMPT"
- Inject sessionId as context prefix if provided: "[session: SESSION_ID]\n\nPROMPT"
- Collect stdout into result string
- Capture stderr separately
- Hard timeout: 5 minutes (300_000 ms)
- On timeout: kill child process, reject with readable error
- On non-zero exit code without stdout: reject with stderr content
- On zero exit with empty stdout: resolve with "Done."

### src/db.ts
- Initialize better-sqlite3 database at store/geminiclaw.db
- Table: sessions (chat_id TEXT PRIMARY KEY, session_id TEXT, updated_at INTEGER)
- Function: getSessionId(chatId: string): string — get or create UUID session_id
- Function: resetSession(chatId: string): string — generate new UUID, update DB, return it

### src/bot.ts
- Import Bot from grammy
- Import runGemini from ./gemini
- Import getSessionId, resetSession from ./db
- Import env from ./env
- Create message queue per chat_id (Map<string, Promise<void>>)

#### Commands to implement

**/start**
Reply: "GeminiClaw запущен. Пиши задачи, отправляй файлы. /help для команд."

**/help**
Reply with command list:
- /newchat — начать новую сессию
- /status — статус бота и сессии
- /chatid — показать твой chat ID
- /compact — сжать контекст
- /checkpoint — сохранить прогресс
- /model [pro|flash|auto] — выбор модели
- /recall <запрос> — поиск в истории
- /memory — показать активные воспоминания
- /dream — консолидация памяти
- /selfaudit — проверка системы
- /schedule — управление задачами по расписанию

**/newchat**
1. Call resetSession(chatId) to generate new session_id
2. Reply: "Новая сессия начата. Контекст предыдущей сохранён в памяти."

**/status**
Implement directly in Node (do not spawn gemini for this):
- Show session_id (first 8 chars) for current chat
- Show bot uptime: process.uptime() formatted as "Xч Yм"
- Show memory file status: check if ~/obsidian-vault/GeminiClaw/agent-memory.md exists

**/chatid**
Reply: `Твой chat ID: ${ctx.chat.id}`

#### Message handling

For every non-command text message:
1. Check ALLOWED_CHAT_ID whitelist — if not allowed, silently return
2. Add to per-chat queue (serial execution, one at a time)
3. Send typing indicator every 4 seconds while waiting
4. Get sessionId from DB
5. Call runGemini(message, sessionId)
6. Split response if > 4096 chars (split at newlines, not mid-word)
7. Send each chunk as separate message
8. On error: reply with truncated error message (max 3500 chars)

#### Long message splitter
Function splitMessage(text: string, maxLen = 4000): string[]
- Split at paragraph boundaries (\n\n) when possible
- Fall back to line boundaries (\n)
- Fall back to hard cut at maxLen
- Never return empty array — always at least one chunk

#### Typing indicator
Use setInterval with ctx.replyWithChatAction('typing') every 4000ms.
Clear interval in finally block.

### src/index.ts
- Import startBot from ./bot
- Call startBot().catch(err => { console.error(err); process.exit(1) })

#### Graceful shutdown
Handle SIGTERM and SIGINT:
- Stop accepting new messages (bot.stop())
- Wait for active queue to drain (max 30 seconds)
- Exit with code 0

## GEMINI.md (project instructions file)
Create this file at project root:
```
# GeminiClaw

You are an AI assistant accessible through Telegram.

## Owner
- Language: match the user's language (default Russian)
- Style: direct, concise, lead with result
- No AI clichés, no sycophancy

## Working Rules
- Execute tasks, do not narrate plans
- Save artifacts to workspace/output/
- Save incoming files to workspace/inbox/
- Verify results before finalizing

## Memory
- Long-term facts: ~/obsidian-vault/GeminiClaw/agent-memory.md
- Check this file before answering thematic questions
- Update it after significant tasks
```

## After all files are created

```bash
npm run build
pm2 start ecosystem.config.js
pm2 save
pm2 list
```

Test: send any text to the bot in Telegram. It should respond.

Verify pm2 shows geminiclaw as online.
```

## Команды для запуска после генерации кода

```bash
npm run build
pm2 restart geminiclaw
pm2 logs geminiclaw --lines 20
```

## Troubleshooting

**Бот не отвечает на сообщения**
Проверь логи: `pm2 logs geminiclaw --lines 50`
Убедись, что `ALLOWED_CHAT_ID` совпадает с твоим реальным chat ID (используй /chatid или @userinfobot).

**`spawn gemini ENOENT`**
Gemini CLI не найден в PATH для процесса PM2. Передай полный путь:
```bash
which gemini   # найди полный путь, например /usr/local/bin/gemini
```
Добавь в `ecosystem.config.js` в блок `env`: `PATH: process.env.PATH`

**Ответы приходят только частично (обрывается на середине)**
Timeout слишком короткий для длинных задач. Увеличь в `src/gemini.ts` с 300_000 до 600_000.

## После этого шага

- [ ] `npm run build` без ошибок
- [ ] `pm2 list` показывает `geminiclaw` online
- [ ] Бот отвечает на текстовое сообщение в Telegram
- [ ] /start возвращает приветствие
- [ ] /chatid возвращает твой числовой ID
- [ ] /newchat создаёт новую сессию

Следующий шаг: [[05_NATIVE_MEDIA]]

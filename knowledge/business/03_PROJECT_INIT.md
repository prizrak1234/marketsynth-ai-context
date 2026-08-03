---
tags: [gemini, setup, nodejs, npm, typescript]
date: 2026-04-18
type: note
---

# Шаг 3: Инициализация проекта

## Prerequisites

- Node.js 22+ установлен (`node -v`)
- Gemini CLI авторизован
- `.env` создан с токенами

## 1. Создать структуру папок

```bash
mkdir -p ~/GeminiClaw
cd ~/GeminiClaw
mkdir -p src workspace/inbox workspace/output/logs workspace/tmp store agents
touch workspace/inbox/.gitkeep workspace/output/.gitkeep
```

## Структура проекта

```text
GeminiClaw/
  package.json
  tsconfig.json
  ecosystem.config.js
  .gitignore
  .env
  GEMINI.md              <- инструкции для агента (аналог AGENTS.md)
  workspace/
    inbox/               <- входящие файлы от пользователя
    output/              <- артефакты агента
    tmp/                 <- временные файлы
  src/
    index.ts
    bot.ts
    gemini.ts
    env.ts
    memory.ts
    scheduler.ts
  store/
    geminiclaw.db        <- SQLite база
  agents/                <- субагенты
```

## 2. Установить зависимости

```bash
npm init -y
npm install grammy better-sqlite3 cron-parser pino pino-pretty dotenv
npm install -D typescript @types/node @types/better-sqlite3 ts-node
```

**Что и зачем:**
- `grammy` — Telegram Bot API фреймворк
- `better-sqlite3` — синхронный SQLite (память, история, планировщик)
- `cron-parser` — разбор cron-выражений для планировщика
- `pino` / `pino-pretty` — структурированные логи
- `dotenv` — загрузка `.env`

## 3. tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "Node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true
  },
  "include": ["src/**/*.ts"]
}
```

## 4. ecosystem.config.js

Создай файл `ecosystem.config.js` в корне проекта:

```js
module.exports = {
  apps: [{
    name: 'geminiclaw',
    script: 'dist/index.js',
    env: { NODE_OPTIONS: '--no-deprecation' },
    max_memory_restart: '300M',
    restart_delay: 3000,
    max_restarts: 10
  }]
}
```

**Параметры:**
- `max_memory_restart: '300M'` — автоматический рестарт при утечке памяти
- `restart_delay: 3000` — 3 секунды перед рестартом (защита от loop-краша)
- `max_restarts: 10` — после 10 крашей PM2 прекращает рестарты (нужно смотреть логи)

## 5. .gitignore

```gitignore
node_modules/
dist/
.env
store/
workspace/inbox/*
workspace/output/*
workspace/tmp/*
!workspace/inbox/.gitkeep
!workspace/output/.gitkeep
```

## 6. Первичная компиляция и запуск

```bash
npm run build
pm2 start ecosystem.config.js
pm2 list
```

## Troubleshooting

**`better-sqlite3` не собирается (build error)**
Нужны инструменты компиляции:
```bash
apt install -y build-essential python3
npm install -D node-gyp
```

**`Cannot find module 'grammy'`**
`npm install` не был выполнен или завершился с ошибкой. Повтори:
```bash
rm -rf node_modules package-lock.json
npm install
```

**PM2 показывает `errored` вместо `online`**
Смотри логи: `pm2 logs geminiclaw --lines 30`

## 7. Создание GEMINI.md (Конституция агента)

Это самый важный файл. Он определяет, как бот будет общаться и какие правила соблюдать. Без него Gemini будет вести себя как обычный "вежливый чат-бот" с кучей лишнего текста.

Создай файл `GEMINI.md` в корне:

```markdown
# GeminiClaw (Core Mandates)

## 1. Silent Execution Rule (CRITICAL)
NEVER output intermediate steps, tool calls, or thinking process.
- Forbidden phrases: "I will now...", "I'll search...", "Searching...", "Updating...", "Внедрил...", "Сделал...".
- **Do the work. Then output only the final result.**

## 2. Personality & Style
- Language: Match the user's language (Default: Russian).
- Tone: Direct, no fluff, no clichés ("Certainly!", "Great question!").
- NO POST-TASK SUMMARIES: Do not narrate what you've just done. Say "Готово" or show the result.
- No "maybe", "perhaps", "you could try".
- Default to plain text in Telegram. No files unless explicitly asked.

## 3. Autonomy Matrix
1. **AUTONOMOUS (No approval needed):** Research, reading files, temporary shell commands, updating memory.
2. **CRITICAL (Approval REQUIRED):** Modifying source code in `src/`, deleting files, changing core config.
```

## После этого шага

- [ ] Папка `~/GeminiClaw` существует со структурой
- [ ] `node_modules/` содержит все пакеты
- [ ] `ecosystem.config.js` создан
- [ ] `npm run build` завершается без ошибок
- [ ] `pm2 list` показывает процесс (пока без бота — он будет в следующем шаге)

Следующий шаг: [[04_TELEGRAM_BRIDGE]]

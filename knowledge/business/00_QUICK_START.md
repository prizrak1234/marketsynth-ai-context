---
tags: [gemini, quickstart, install]
date: 2026-04-18
type: note
---

# Быстрый старт: готовый репо GeminiClaw

Для тех, кто хочет запустить всё за 10 минут без ручной сборки.

## Prerequisites

- Ubuntu 22.04+ или Debian 12+
- SSH-доступ к серверу (или локальный терминал)
- Google-аккаунт (для gemini login) или API-ключ из AI Studio
- Telegram-бот токен (получить через @BotFather)

## Установка одной последовательностью

```bash
# 1. Обновить систему
apt update && apt upgrade -y

# 2. Установить Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
node -v   # должен вернуть v22.x.x

# 3. Установить Gemini CLI и PM2
npm install -g @google/gemini-cli pm2
gemini --version
pm2 -v

# 4. Авторизоваться в Gemini
gemini login
# Следуй инструкциям в браузере. На сервере без GUI: скопируй URL и открой на ПК.

# 5. Клонировать репо
git clone https://github.com/[username]/GeminiClaw.git
cd ~/GeminiClaw

# 6. Создать .env из шаблона
cp .env.example .env
nano .env
# Заполни TELEGRAM_BOT_TOKEN и ALLOWED_CHAT_ID

# 7. Собрать и запустить
npm install
npm run build
pm2 start ecosystem.config.js

# 8. Автозапуск после перезагрузки сервера
pm2 startup
# Скопируй и выполни команду, которую выдаст pm2 startup
pm2 save

# 9. Проверить статус
pm2 list
```

## Что означает каждый шаг

**`cp .env.example .env`** — создаёт файл с переменными окружения из шаблона. Без него бот не запустится.

**`npm install`** — скачивает все зависимости (grammy, better-sqlite3, pino, dotenv и др.).

**`npm run build`** — компилирует TypeScript в JavaScript в папку `dist/`.

**`pm2 start ecosystem.config.js`** — запускает бот как фоновый процесс с автоматическим рестартом при краше.

**`pm2 startup && pm2 save`** — регистрирует PM2 в systemd, чтобы бот поднимался автоматически после перезагрузки VDS.

## Минимальный .env

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFxxxxxxxxxxxxxxxxx
ALLOWED_CHAT_ID=987654321
# GOOGLE_API_KEY=   # только если используешь API Key режим
```

## Troubleshooting

- `git clone` не работает: проверь, установлен ли git — `apt install -y git`
- `npm run build` падает с ошибками TypeScript: убедись, что Node.js v22+ (`node -v`)
- Бот не отвечает после запуска: проверь логи `pm2 logs geminiclaw --lines 50`

## После этого шага

- [ ] `pm2 list` показывает `geminiclaw` со статусом `online`
- [ ] Бот отвечает на сообщение в Telegram
- [ ] `pm2 startup && pm2 save` выполнены

Если собираешь с нуля (без готового репо): [[01_INSTALL]]

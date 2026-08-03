---
tags: [gemini, tutorial, guide, index]
date: 2026-04-18
type: note
version: v3.1
---

# Сборка GeminiClaw v3.1: Полный гайд (2026)

Оглавление для создания AI-агента на базе Gemini CLI, управляемого через Telegram.

---

## Быстрый старт: склонировать готовый репо

Если хочешь запустить всё сразу без ручной сборки:

```bash
git clone https://github.com/[username]/GeminiClaw.git
cd GeminiClaw
cp .env.example .env
# отредактируй .env — вставь токены
npm install && npm run build
pm2 start ecosystem.config.js
pm2 startup && pm2 save
```

Подробности: [[00_QUICK_START]]

---

## Пошаговая сборка

| Шаг | Файл                   | Что делаем                                    |
| --- | ---------------------- | --------------------------------------------- |
| 0   | [[00_QUICK_START]]     | Быстрый старт через готовый репо              |
| 1   | [[01_INSTALL]]         | Установка Node.js, Gemini CLI, PM2            |
| 2   | [[02_AUTH_AND_LIMITS]] | Авторизация Google, настройка .env            |
| 3   | [[03_PROJECT_INIT]]    | Структура проекта, npm зависимости            |
| 4   | [[04_TELEGRAM_BRIDGE]] | Telegram бот на grammY                        |
| 5   | [[05_NATIVE_MEDIA]]    | Голосовые, кружочки, фото, документы          |
| 6   | [[06_HYBRID_MEMORY]]   | Трёхуровневая память (SQLite + md + Obsidian) |
| 7   | [[07_ADVANCED_ARCH]]   | Compaction, topic shift, subagents            |
| 8   | [[08_GWS_SEARCH]]      | Google Workspace, Firecrawl                   |
| 9   | [[09_SCHEDULER]]       | Планировщик задач на SQLite                   |
| 10  | [[10_COMMANDS]]        | Все команды управления ботом                  |
| 11  | [[11_PRODUCTION]]      | Финальный продакшн чеклист                    |

---

## Почему Gemini CLI

- Контекст 2 000 000 токенов: вмещает целые кодовые базы
- Бесплатный вход через Google-аккаунт (до 1000-2000 запросов/день)
- Нативная мультимодальность: видео, аудио, фото без внешних API
- Синтаксис `@file` для прямой передачи файлов в контекст

---

*GeminiClaw v3.1. Собрано Игорем Зуевичем.*

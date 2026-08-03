---
tags: [gemini, auth, limits, env, security]
date: 2026-04-18
type: note
---

# Шаг 2: Авторизация и лимиты

## Prerequisites

- Выполнен Шаг 1 (Node.js 22, Gemini CLI установлены)
- Есть Google-аккаунт или API-ключ из AI Studio
- Есть Telegram-бот токен (получить через @BotFather)
- Известен твой Telegram chat ID

## Способы авторизации Gemini

### Вариант А: Google OAuth (рекомендуется)

```bash
gemini login
```

Используются лимиты твоей подписки Google. Без подписки — до 1000 запросов/день бесплатно.

**Лимиты по типу аккаунта:**
- Обычный Google: ~1 000 запросов/день
- Google One AI Premium (Pro): ~1 500 запросов/день
- Google One AI Ultra: ~2 000 запросов/день

### Вариант Б: API Key (для серверов)

Ключ из [aistudio.google.com](https://aistudio.google.com/) — вкладка "Get API key".

```bash
export GOOGLE_API_KEY="ВАШ_КЛЮЧ"
# Или добавь в .env (рекомендуется)
```

## Шаблон .env файла

Создай файл `.env` в папке проекта:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFxxxxxxxxxxxxxxxxx
ALLOWED_CHAT_ID=987654321
# GOOGLE_API_KEY=   # только если используешь API Key режим, иначе оставь закомментированным
```

**Важно:** `.env` никогда не коммитится в git. Убедись, что `.gitignore` содержит строку `.env`.

## Как узнать свой ALLOWED_CHAT_ID

1. Открой Telegram
2. Найди бота `@userinfobot`
3. Отправь ему любое сообщение
4. Он вернёт твой числовой chat ID

Или напиши своему боту любое сообщение после запуска, добавь временный обработчик и проверь `ctx.chat.id` в логах.

## Почему ALLOWED_CHAT_ID критически важен

Без этой переменной любой человек, узнавший username твоего бота, получит доступ к твоему AI-агенту с доступом к файловой системе сервера. Это не опциональная настройка безопасности — это обязательная.

Бот должен проверять chat ID в самом начале каждого обработчика:

```typescript
if (String(ctx.chat.id) !== env.ALLOWED_CHAT_ID) return
```

## Проверка авторизации Gemini

После настройки `.env`:

```bash
gemini "ответь одним словом: работает"
```

Должен получить короткий ответ без ошибок авторизации.

## Troubleshooting

**`Error: TELEGRAM_BOT_TOKEN is missing`**
Файл `.env` не создан или находится не в папке проекта. Проверь: `ls -la ~/GeminiClaw/.env`

**`gemini login` прошёл, но через день перестал работать**
Токен OAuth мог истечь. Повтори `gemini login`.

**Хочу использовать API Key, но не знаю где взять**
Зайди на [aistudio.google.com](https://aistudio.google.com/), войди под Google-аккаунтом, нажми "Get API key" в левом меню.

## После этого шага

- [ ] `.env` создан с TELEGRAM_BOT_TOKEN и ALLOWED_CHAT_ID
- [ ] `.gitignore` содержит `.env`
- [ ] `gemini "ответь одним словом: работает"` возвращает ответ
- [ ] Ты знаешь свой chat ID

Следующий шаг: [[03_PROJECT_INIT]]

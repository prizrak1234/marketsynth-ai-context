---
title: "Google Workspace CLI — подключение к ClaudeClaw"
date: 2026-03-12
tags:
  - claudeclaw
  - gws
  - google-workspace
  - tutorial
type: reference
status: active
---

# Google Workspace CLI — подключение к ClaudeClaw

GWS CLI — инструмент от сотрудников Google (не официальный продукт), который даёт Claude Code прямой доступ к Gmail, Drive, Calendar, Docs, Sheets, Slides через одну команду в терминале. Без Zapier, без n8n, без кода.

## Что это даёт

После подключения ты можешь писать в Telegram:
- "прочитай 10 последних писем и расставь приоритеты"
- "найди последний документ в Drive"
- "создай Google Doc из этого анализа видео"
- "что у меня стоит в Calendar на завтра"
- "добавь встречу на пятницу в 15:00"

## Что потребуется

- VPS с Node.js (уже есть если ClaudeClaw работает)
- Google-аккаунт (рекомендуется sandbox, не основной)
- Google Cloud Console (бесплатно, нужен биллинг для Model Armor)
- 20-30 минут

---

## Шаг 1 — Установка GWS CLI

На сервере (SSH):

```bash
npm install -g @googleworkspace/cli
gws version
```

Должно вывести: `gws 0.11.1` (или новее).

---

## Шаг 2 — Google Cloud Console

1. Открой https://console.cloud.google.com
2. Создай новый проект → назови `claudeclaw-gws`
3. Включи биллинг (Billing → Link a billing account)

> ⚠️ Биллинг обязателен из-за Model Armor API. Реальные расходы при обычном использовании — копейки или ноль.

---

## Шаг 3 — Включи нужные APIs

В Google Cloud Console → **APIs & Services** → **Enable APIs and Services**

Включи каждый из этих:
- Gmail API
- Google Drive API
- Google Calendar API
- Google Docs API
- Google Sheets API
- Google Slides API
- Model Armor API

---

## Шаг 4 — OAuth Consent Screen

**APIs & Services** → **OAuth consent screen**:

1. User Type: **External** → Create
2. App name: `ClaudeClaw`
3. User support email: твой email
4. Developer contact: твой email
5. Save and Continue (через все шаги)
6. В конце нажми **Publish App** ← ВАЖНО

> Если не нажать Publish App — Google будет требовать повторную авторизацию каждые 7 дней.

---

## Шаг 5 — Создай OAuth Client

**APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**:

1. Application type: **Desktop app**
2. Name: `claudeclaw-desktop`
3. Create
4. Скачай JSON файл (кнопка Download)

---

## Шаг 6 — Положи credentials на сервер

Создай папку:
```bash
mkdir -p ~/.config/gws
```

Скопируй скачанный JSON файл в `~/.config/gws/` и переименуй:
```bash
cp ~/Downloads/client_secret_*.json ~/.config/gws/client_secret.json
```

Или через SFTP/SCP скинь файл напрямую на сервер.

---

## Шаг 7 — OAuth авторизация

> ⚠️ Это самый хитрый шаг на headless VPS. Нужен SSH port forwarding.

**На своём компьютере** открой два терминала:

Терминал 1 — туннель:
```bash
ssh -L 40793:localhost:40793 root@<IP_СЕРВЕРА>
```
Держи это соединение открытым.

Терминал 2 — на сервере:
```bash
gws auth login --scopes "https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/presentations"
```

GWS выдаст URL → открой его в браузере → авторизуйся → Google перенаправит на `localhost:40793` → через туннель callback попадёт на сервер → credentials сохранятся автоматически.

---

## Шаг 8 — Проверка

```bash
gws auth status
```

Должно показать:
```json
{
  "token_valid": true,
  "user": "твой@gmail.com",
  "auth_method": "oauth2"
}
```

Тест доступа к Drive:
```bash
gws drive files list --params '{"pageSize": 5, "orderBy": "modifiedTime desc"}' --format table
```

---

## Примеры команд

### Gmail
```bash
# Последние 10 писем
gws gmail users messages list --params '{"userId": "me", "maxResults": 10}' --format table

# Непрочитанные
gws gmail users messages list --params '{"userId": "me", "labelIds": ["UNREAD"], "maxResults": 20}' --format table
```

### Drive
```bash
# Последние файлы
gws drive files list --params '{"pageSize": 10, "orderBy": "modifiedTime desc", "fields": "files(id,name,mimeType,modifiedTime)"}' --format table

# Поиск файла
gws drive files list --params '{"q": "name contains '\''отчёт'\''", "pageSize": 5}' --format table
```

### Calendar
```bash
# События на сегодня
gws calendar events list --params '{"calendarId": "primary", "maxResults": 10, "singleEvents": true, "orderBy": "startTime", "timeMin": "2026-03-12T00:00:00Z"}' --format table
```

### Docs — создать документ
```bash
gws docs documents create --json '{"title": "Мой новый документ"}'
```

---

## Как ClaudeClaw использует GWS

После подключения ClaudeClaw автоматически вызывает GWS когда ты просишь что-то связанное с Google-сервисами. Примеры в Telegram:

- "покажи последние письма" → `gws gmail users messages list`
- "создай doc из этого текста" → `gws docs documents create`
- "что в Drive последнее?" → `gws drive files list`

---

## Troubleshooting

**"No credentials provided"** — OAuth не завершился. Повтори Шаг 7 с SSH туннелем.

**"Request had insufficient authentication scopes"** — авторизовался без нужных скоупов. Запусти `gws auth logout` и повтори авторизацию с полным списком `--scopes`.

**"Publish App" не нажал** — каждые 7 дней Google сбрасывает токен. Зайди в OAuth consent screen и нажми Publish.

**Биллинг не включён** — Model Armor API вернёт 403. Включи биллинг в Google Cloud Console.

---

## Ссылки

- GitHub: https://github.com/googleworkspace/cli
- Google Cloud Console: https://console.cloud.google.com
- OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent

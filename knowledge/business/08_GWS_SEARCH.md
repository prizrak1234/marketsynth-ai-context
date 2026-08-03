---
tags: [gemini, gws, tools, firecrawl, google-workspace]
date: 2026-04-18
type: note
---

# Шаг 8: Инструменты (Google Workspace, Firecrawl, поиск)

## Prerequisites

- Шаг 7 выполнен
- `gws` CLI установлен (если нужна интеграция с Google Workspace)
- API-ключ Firecrawl (если нужен парсинг сайтов)

## 1. Google Workspace через gws CLI

### Проверка установки

```bash
gws --help
```

Если gws не установлен, установи его:
```bash
npm install -g @google/gws-pro
```

Если команда не найдена — gws не установлен. Это опциональный инструмент; пропусти если не нужен.

### Пример реального вызова

```bash
# Список файлов на Google Drive
gws drive files list --params '{"pageSize": 10, "orderBy": "modifiedTime desc"}'

# Список событий в календаре
gws calendar events list --params '{"calendarId": "primary", "maxResults": 5}'

# Последние 5 писем в Gmail
gws gmail users messages list --params '{"userId": "me", "maxResults": 5}'

# Получить Google Sheets
gws sheets spreadsheets get --params '{"spreadsheetId": "SPREADSHEET_ID"}'
```

### Добавить в GEMINI.md

```markdown
## Google Workspace
- Use `gws` CLI for Drive, Sheets, Gmail, Calendar, Docs, Tasks operations
- Credentials at ~/.config/gws/credentials.enc
- Account: [твой email]
- Usage: gws {service} {method} --params '{...}'
- Inspect schema: gws schema {method}
```

### Переменные окружения (добавь в .env)

```env
GWS_ACCOUNT=your@email.com
```

## 2. Firecrawl для веб-скрапинга

Firecrawl работает через API или через MCP. Для GeminiClaw используй HTTP API напрямую.

### Через HTTP API

```bash
# Добавь в .env
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxx

# Пример скрапинга страницы
curl -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["markdown"]}'
```

### Добавить в GEMINI.md

```markdown
## Web Scraping
- Use Firecrawl API when FIRECRAWL_API_KEY is set in env
- Endpoint: POST https://api.firecrawl.dev/v1/scrape
- Payload: {"url": "URL", "formats": ["markdown"]}
- Save scraped content to workspace/output/
- Triggers: "скрапи", "собери данные с", "проанализируй страницу"
```

### Через Claude с MCP (альтернатива)

Firecrawl также доступен как MCP-сервер. Если у тебя установлен Claude Code CLI с MCP `firecrawl`, то внутри Claude сессии инструменты `firecrawl_scrape`, `firecrawl_crawl`, `firecrawl_search` доступны напрямую.

**Важно:** это работает только внутри Claude Code, не в GeminiClaw. Для GeminiClaw используй HTTP API выше.

## 3. Встроенный поиск Google (Google Grounding)

Gemini CLI поддерживает нативный поиск Google. Это не требует никаких ключей.

Добавить в GEMINI.md:

```markdown
## Web Search
- For current facts, prices, news, API changes: use Google search natively
- Gemini CLI has built-in Google Grounding when using default model
- For latest info: ask user to enable grounding or use: gemini --grounding "QUERY"
- Do not claim latest information without search enabled
```

## 4. GitHub CLI (опционально)

```bash
apt install -y gh
gh auth login
```

Добавить в GEMINI.md:

```markdown
## GitHub
- Use `gh` CLI for repo, issue, and PR operations
- Requires: gh auth login (done once)
```

## Промпт для обновления GEMINI.md

```text
Update GEMINI.md to add tool integration rules for all configured external tools.

Check which tools are actually available on this server:
1. Run: which gws && gws --help | head -5
2. Run: echo $FIRECRAWL_API_KEY | cut -c1-10
3. Run: which gh && gh --version

For each tool that IS available: add the usage rules to GEMINI.md under ## Tools section.
For each tool NOT available: skip it — do not add phantom instructions.

Keep the Tools section concise — 2-4 lines per tool.
```

## Troubleshooting

**`gws: command not found`**
GWS CLI не установлен или не в PATH. Это опциональный инструмент — пропусти если не нужен.

**Firecrawl возвращает 401**
Неверный API-ключ. Проверь `.env` и убедись, что переменная загружается: `echo $FIRECRAWL_API_KEY`

**`gh auth login` не работает на headless сервере**
Используй: `gh auth login --with-token < token.txt` (создай файл с персональным токеном GitHub).

## После этого шага

- [ ] `gws --help` работает (если установлен)
- [ ] Firecrawl API вызов возвращает markdown (если нужен)
- [ ] GEMINI.md обновлён с актуальными инструментами
- [ ] Только реально работающие инструменты добавлены в инструкции

Следующий шаг: [[09_SCHEDULER]]
